# Snapshotalyer-3000

Demo project to manage AWS EC2 instance snapshots

##About

This project is a demo, and uses boto3 to manage AWS EC2 instance snapshots

## Configuring

shotty uses the configuration file created by the AWS cli. e.g.

`aws configure --profile shotty`

## Running

`pipenv run python shotty/shotty.py <configurations> <command> <subcommand> <--project=PROJECT> <--instance=INSTANCE`

*configurations* sets the profile or region
*command* is instances, volumes, or snapshots list, start, or stop
*subcommand* - depends on command
*project|instance|--force|--all* is required to fine grain solutions
