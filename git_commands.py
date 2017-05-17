
class GitCommands:

    CREATE_NEW_BRANCH = 'git branch {branch_name}'
    CHECKOUT_BRANCH = 'git checkout {branch_name}'

    ADD_ALL_FILES = 'git add --all'
    COMMIT_CHANGES = 'git commit -a -m "{msg}"'

    PUSH_CHANGES = 'git push origin {branch_name}'
    PULL_CHANGES = 'git pull origin {branch_name}'
