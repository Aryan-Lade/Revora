from app.services import context as context_service, scoring, audit
from app.recovery import detector, executor, guardrails, risk, strategies
from app.ai import provider as ai_provider
from app.ml import model as ml_model
from app.policy import engine as policy_engine_module
from app.channels.selector import select as select_channel
from app.gateway import pool as gateway_pool
from app.voice import agent as voice_agent
from app.razorpay import client as razorpay_client
from app.database import models
from app.core import errors
from app.core.constants import EMAIL
from app.state import recovery_state
from sqlalchemy.orm import Session


def observe_case(db: Session, case_id: int):
    """
    Observe step: gather information about the case.
    """
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise errors.NotFound(f"Recovery case {case_id} not found")
    ctx = context_service.build(db, case)
    return ctx


def predict_recovery(ctx: dict):
    recovery_probability = ml_model.predict_recovery_probability(ctx)
    return recovery_probability


def reason_about_case(ctx: dict, recovery_probability: float):
    """
    Reason step: use AI to diagnose and recommend action.
    """
    ai_rec = ai_provider.ai_provider.get_recovery_recommendation(ctx, recovery_probability)
    return ai_rec


def plan_action(ctx: dict, ai_rec, db: Session):
    """
    Plan step: check policy and guardrails, select channel.
    """
    from app.policy.engine import policy_engine
    from app.recovery.guardrails import guardrail_engine

    case_id = ctx["case"]["id"]
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()

    # Check policy using evaluate(context, channel)
    channel = getattr(ai_rec, "recommended_channel", EMAIL)
    policy_decision = policy_engine.evaluate(ctx, channel)
    if not policy_decision.allowed:
        raise errors.PolicyBlocked(message="Policy blocked", detail={"reason": policy_decision.reason})

    # Check guardrails using evaluate(context, action)
    action = getattr(ai_rec, "recommended_action", "EMAIL")
    guardrail_decision = guardrail_engine.evaluate(ctx, action)
    if not guardrail_decision.allowed:
        raise errors.GuardrailBlocked(message="Guardrail blocked", detail={"reason": guardrail_decision.reason})

    # Select channel
    channel_selection = select_channel(db=db, case=case, context=ctx)

    return {
        "policy_decision": policy_decision,
        "guardrail_decision": guardrail_decision,
        "channel_selection": channel_selection
    }


def act_on_plan(case_id: int, plan_result: dict, db: Session):
    """
    Act step: execute the recovery action.
    """
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise errors.NotFound(f"Recovery case {case_id} not found")

    channel_selection = plan_result.get("channel_selection")
    if channel_selection is None:
        raise errors.GuardrailBlocked(message="No channel selected", detail={})

    action_map = {
        EMAIL: "SEND_EMAIL",
        "VOICE_AI": "INITIATE_CALL",
        "PAYMENT_LINK": "CREATE_LINK"
    }
    action = action_map.get(channel_selection.channel, channel_selection.channel)

    # Correct argument order: db, case, channel, action
    result = executor.execute_recovery_action(
        db=db,
        case=case,
        channel=channel_selection.channel,
        action=action,
    )

    return result


def measure_result(case_id: int, action_result: dict, db: Session):
    """
    Measure step: record the outcome and update the case.
    """
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise errors.NotFound(f"Recovery case {case_id} not found")

    db.refresh(case)
    return case
