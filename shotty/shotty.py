import boto3
import botocore
import click

session = boto3.Session(profile_name='shotty')
ec2 = session.resource('ec2')

###################
# Helper functions
###################
def filter_instances2(project, enforcer):
    instances = []
    if project:
        filters=[{'Name':'tag:Project','Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    elif enforcer:
        instances = ec2.instances.all()
    else:
        print("You must set a project or --force")

    return instances

def filter_instances(project):
    instances = []
    if project:
        filters=[{'Name':'tag:Project','Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()

    return instances

def has_pending_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'pending'

#################
# CLI group
#################
@click.group()
#@click.command()
@click.option('--profile', default='shotty')
def cli(profile):
    """Shotty manages snapshots"""
    global ec2
    ec2 = boto3.Session(profile_name=profile).resource('ec2')

##################
# volumes
##################
@cli.group('volumes')
def volumes():
    """Commands for volumes"""

@volumes.command('list')
@click.option('--project', default=None,
    help="Only volumes for project (tag Project:<name>)")
def list_volumes(project):
    "List EC2 volumes"

    instances = filter_instances(project)

    for i in instances:
        for v in i.volumes.all():
            print(', '.join((
                v.id,
                i.id,
                v.state,
                str(v.size) + "GiB",
                v.encrypted and "Encrypted" or "Not Encrypted"
            )))

    return

#################
# Snapshots
#################
@cli.group('snapshots')
def snapshots():
    """Commands for snapshots"""

@snapshots.command('list')
@click.option('--project', default=None,
    help="Only snapshots for project (tag Project:<name>)")
@click.option('--all', 'list_all', default=False, is_flag=True,
    help="List all snapshots for each volume, not just the most recent")
def list_snapshots(project, list_all):
    "List Snapshots"
    instances = filter_instances(project)

    for i in instances:
        for v in i.volumes.all():
            for s in v.snapshots.all():
                print(', '.join((
                    s.id,
                    v.id,
                    i.id,
                    s.state,
                    s.progress,
                    s.start_time.strftime("%c")
                )))

                if s.state == 'completed' and not list_all: break
    return

###################
# instances
###################
@cli.group('instances')
def instances():
    """Commands for instances"""

@instances.command('snapshot',
    help="Create snapshot of all volumes")
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--force', 'enforcer', default=False, is_flag=True,
    help="Forces reboot if project isn't set")
def create_snapshots(project, enforcer):
    "Create snapshots for EC2 instances"

    instances = filter_instances2(project, enforcer)

    for i in instances:
        print("Stopping {0}...".format(i.id))
        i.stop()
        i.wait_until_stopped()

        for v in i.volumes.all():
            if has_pending_snapshot(v):
                print("  Skipping {0}, snapshot already in progress".format(v.id))
            print("Creating a snapshot of {0}".format(v.id))
            v.create_snapshot(Description="Created by SnapshotAlyzer 3000")

        print("Startng {0}...".format(i.id))

        i.start()
        i.wait_until_running()

    print("Job is done")

    return

@instances.command('list')
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
def list_instances(project):
    "List EC2 instances"
    instances = filter_instances(project)

    for i in instances:
        tags = {t['Key']: t['Value'] for t in i.tags or []}
        print(', '.join((
        i.id,
        i.instance_type,
        i.placement['AvailabilityZone'],
        i.state['Name'],
        i.public_dns_name,
        tags.get('Project', '<no project>')
        )))

    return

@instances.command('reboot')
@click.option('--project', default=None,
    help='Only instances for project')
@click.option('--force', 'enforcer', default=False, is_flag=True,
    help="Forces reboot if project isn't set")
def reboot_instances(project, enforcer):
    "Reboot EC2 instances"

    instances = filter_instances2(project, enforcer)

    for i in instances:
        print ("Rebooting {0}".format(i.id))
        try:
            i.reboot()
        except botocore.exceptions.ClientError as e:
            print(" Could not reboot {0}: {1}".format(i.id, str(e)))
            continue

@instances.command('stop')
@click.option('--project', default=None,
    help='Only instances for project')
@click.option('--force', 'enforcer', default=False, is_flag=True,
    help="Forces reboot if project isn't set")
def stop_instances(project, enforcer):
    "Stop EC2 instances"

    instances = filter_instances2(project, enforcer)

    for i in instances:
        print ("Stopping {0}".format(i.id))
        try:
            i.stop()
        except botocore.exceptions.ClientError as e:
            print(" Could not stop {0}: {1}".format(i.id, str(e)))
            continue

@instances.command('start')
@click.option('--project', default=None,
    help='Only instances for project')
@click.option('--force', 'enforcer', default=False, is_flag=True,
    help="Forces reboot if project isn't set")
def start_instances(project, enforcer):
    "Start EC2 instances"

    instances = filter_instances2(project, enforcer)

    for i in instances:
        print ("Starting {0}".format(i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print(" Could not start {0}: {1}".format(i.id, str(e)))
            continue

if __name__ == '__main__':
    cli()
