### Setup

Install airflow per its instructions, and copy the dags and plugins directories from this repo into the AIRFLOW_HOME folder.

Launch airflow using `airflow standalone`.
Configure a GH connection with the name "github_default" and a PAT.

To setup receiving webhooks onto the local airflow instance, install the webhook forwarder gh extension, and run
```
gh webhook forward --events=pull_request -R criemen/test-webhooks -U http://localhost:8080/github_hook --secret secret
```

Open a PR on your repository, and magic should happen!
