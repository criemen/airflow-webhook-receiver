from flask import Blueprint, request, make_response, abort
from airflow.plugins_manager import AirflowPlugin
from airflow.www.app import csrf
from airflow.api.common.trigger_dag import trigger_dag
import hmac
import hashlib
webhook_listener_bp = Blueprint('GHWebhookListener', __name__)

@webhook_listener_bp.route('/github_hook', methods=['GET', 'POST'])
@csrf.exempt
def github_hook():
    """"
    This is a webhook receiver for the Github webhook that is triggered on PR events.

    TODO: Also listen to check events to trigger qlucie on successful check runs for external authors.
    TODO: factor out the hardcoded secret to an airflow variable.
    """
    secret = "secret"
    content = request.json

    # Verify the request signature
    digest = hmac.new(secret.encode(), request.data, hashlib.sha256).hexdigest()
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature or not signature.startswith("sha256="):
        abort(400, "The header X-Hub-Signature is required")

    if not hmac.compare_digest(signature, "sha256=" + digest):
        abort(400, "Invalid signature on incoming webhook request")

    event_name = signature = request.headers.get("X-GitHub-Event")
    print(f"GH webhook payload of event {event_name}, content: {content}")
    print(f"action: {content['action']}")
    if event_name == "pull_request":
        triggered_run = trigger_dag('qlucie_dag', conf={'pr_id': content['number']})
        if triggered_run is None:
            abort(400, "Failed to trigger DAG.")
    return make_response(f"Success", 200)


class GithubWebhookReceiver(AirflowPlugin):
    name = "gh_webhook_receiver"
    flask_blueprints = [webhook_listener_bp]
