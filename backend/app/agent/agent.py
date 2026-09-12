from app.services import context as context_service, audit
from app.recovery import executor
from app.ai import provider as ai_provider
from app.ml import model as ml_model
from app.policy.engine import policy_engine
from app.recovery.guardrails import guardrail_engine
from app.channels.selector import select as select_channel
from app.database import models
from app.core import errors
from app.core.constants import EMAIL, VOICE_AI, PAYMENT_LINK
from app.state import recovery_state
from sqlalchemy.orm import Session

ACTION_MAP = {
    EMAIL: "SEND_EMAIL",
    VOICE_AI: "INITIATE_CALL",
    PAYMENT_LINK: "CREATE_LINK",
}


def observe_case(db: Session, case_id: int):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise errors.NotFound(f"Recovery case {case_id} not found")
    return context_service.build(db, case)


def predict_recovery(ctx: dict):
    return ml_model.predict_recovery_probability(ctx)


def reason_about_case(ctx: dict, recovery_probability: float):
    return ai_provider.ai_provider.get_recovery_recommendation(ctx, recovery_probability)


def plan_action(ctx: dict, ai_rec, db: Session):
    case_id = ctx["case"]["id"]
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    channel = getattr(ai_rec, "recommended_channel", EMAIL)
    policy_decision = policy_engine.evaluate(ctx, channel)
    if not policy_decision.allowed:
        raise errors.PolicyBlocked(message="Policy blocked", detail={"reason": policy_decision.reason})
    action = getattr(ai_rec, "recommended_action", "EMAIL")
    guardrail_decision = guardrail_engine.evaluate(ctx, action)
    if not guardrail_decision.allowed:
        raise errors.GuardrailBlocked(message="Guardrail blocked", detail={"reason": guardrail_decision.reason})
    channel_selection = select_channel(db=db, case=case, context=ctx)
    return {
        "policy_decision": policy_decision,
        "guardrail_decision": guardrail_decision,
        "channel_selection": channel_selection,
    }


def act_on_plan(case_id: int, plan_result: dict, db: Session):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise errors.NotFound(f"Recovery case {case_id} not found")
    channel_selection = plan_result.get("channel_selection")
    if channel_selection is None:
        raise errors.GuardrailBlocked(message="No channel selected", detail={})
    action = ACTION_MAP.get(channel_selection.channel, channel_selection.channel)
    return executor.execute_recovery_action(
        db=db,
        case=case,
        channel=channel_selection.channel,
        action=action,
    )


def measure_result(case_id: int, action_result: dict, db: Session):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise errors.NotFound(f"Recovery case {case_id} not found")
    db.refresh(case)
    return case


def run_agent_cycle(db: Session, case_id: int) -> dict:
    ctx = observe_case(db, case_id)
    prob = predict_recovery(ctx)
    ai_rec = reason_about_case(ctx, prob)
    plan = plan_action(ctx, ai_rec, db)
    action_res = act_on_plan(case_id, plan, db)
    updated_case = measure_result(case_id, action_res, db)
    return {
        "case_id": case_id,
        "recovery_probability": prob,
        "recommendation": {
            "action": ai_rec.recommended_action,
            "channel": ai_rec.recommended_channel,
            "confidence": ai_rec.confidence,
        },
        "action_result": action_res,
        "final_status": updated_case.status,
    }
