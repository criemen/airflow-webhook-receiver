from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.providers.github.operators.github import GithubOperator
from airflow.providers.github.hooks.github import GithubHook
from datetime import datetime, timedelta
import pendulum
import logging

logger = logging.getLogger(__name__)
target_repo = "criemen/test-webhooks"
check_description = "Internal CI run scheduled by Qlucie"

# TODO: Cache this for some time, instead of hitting this API endpoint every time
def get_team_members(team_name="codeql") -> list[str]:
    logger.info(f"Fetching team members for {team_name} from GH org.")
    gh_hook = GithubHook()
    gh = gh_hook.get_conn()
    members = gh.get_organization("github").get_team_by_slug(team_name).get_members()
    return map(lambda x: x.login, members)

@dag(
    schedule=None,
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    tags=["qlucie"],
    params={
        "pr_id": Param(0, "ID of the PR to check", type="integer"),
    }
)
def qlucie_dag():
    """
    Task to trigger external CI on a given PR.

    TODO: Should use a GH App token instead for authentication.
    TODO: Should check for external users (successful check runs on known workflows)
    TODO: Check what happens with collaborators (i.e. docs team)
    """
    @task()
    def trigger_internal_ci(params=None):
        logger.info(f"Param: {params['pr_id']}.")
        pr_id = params['pr_id']
        if pr_id == 0:
            logger.info("No PR ID specified, aborting.")
            return
        gh_hook = GithubHook()
        gh = gh_hook.get_conn()
        repo = gh.get_repo(target_repo)
        pr = repo.get_pull(pr_id)
        author = pr.user.login
        head_commit = repo.get_commit(pr.head.sha)
        logger.info(f"Retrieved PR with ID {pr.id} from repo {target_repo} with author {author}, head commit sha: {head_commit.sha}.")
        internal_user = author in get_team_members()
        if internal_user:
            logger.info(f"Author {author} is an internal user.")
        else:
            logger.info(f"Author {author} is NOT an internal user, aborting as the path for external users is not implemented.")
            return
        combined_status = head_commit.get_combined_status()
        check_object = [x for x in combined_status.statuses if x.context == 'Checks']
        logger.info(f"Combined status: {combined_status.statuses} and check_object {check_object}.")
        if len(check_object) == 0 or (check_object[0].state == "pending" and check_object[0].description == check_description):
            logger.info(f"Check {check_description} not found or still pending, enqueuing qlucie run.")
            head_commit.create_status(
                state="pending",
                description=check_description,
                context="Checks",
            )
            semmle_code_repo = gh.get_repo("github/semmle-code")
            qlucie_workflow = semmle_code_repo.get_workflow("qlucie.yml")
            # TODO trigger qlucie run here - this is untested, as I've not run on the real gh/codeql repo yet
            # qlucie_workflow.create_dispatch(
            #     ref="main",
            #     inputs={
            #         "pr-number": pr.id,
            #         "status-sha": pr.head.sha,
            #         "sha-override": pr.merge_commit_sha,
            #     }
            # )
        return
    trigger_internal_ci()

qlucie_dag()