import boto3
import botocore
import click

session = boto3.Session(profile_name='shotty')
ec2 = session.resource('ec2')

###################
# Helper functions
###################
def filter_instances3(project, enforcer, my_id):
    instances = []
    filters = []
    if project:
        filters.append({'Name':'tag:Project','Values':[project]})

    if my_id:
        filters.append({'Name':'instance-id','Values':[my_id]})

    if project or my_id:
        instances = ec2.instances.filter(Filters=filters)
    elif enforcer:
        instances = ec2.instances.all()
    else:
        print("You must set a project, instance, or --force")

    return instances

def filter_instances(project, my_i):
    instances = []
    filters = []

    if my_i:
        filters.append({'Name':'instance-id','Values':[my_i]})

    if project:
        filters.append({'Name':'tag:Project','Values':[project]})

    if project or my_i:
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
@click.option('--instance', 'my_id', default=None,
    help="Only specified instance")
def list_volumes(project, my_id):
    "List EC2 volumes"

    instances = filter_instances(project, my_id)

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
@click.option('--instance', 'my_id', default=None,
    help="Only specified instance")
def list_snapshots(project, list_all, my_id):
    "List Snapshots"
    instances = filter_instances(project, my_id)

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
@click.option('--instance', 'my_id', default=None,
    help="Only specified instance")
def create_snapshots(project, enforcer, my_id):
    "Create snapshots for EC2 instances"
    needRestart = False
    instances = filter_instances3(project, enforcer, my_id)

    for i in instances:
        print("Stopping {0}...".format(i.id))
        if i.state['Name'] == 'running' or i.state['Name'] == 'pending':
            i.stop()
            i.wait_until_stopped()
            needRestart = True

        for v in i.volumes.all():
            if has_pending_snapshot(v):
                print("  Skipping {0}, snapshot already in progress".format(v.id))
            print("Creating a snapshot of {0}".format(v.id))
            try:
                v.create_snapshot(Description="Created by SnapshotAlyzer 3000")
            except botocore.exceptions.ClientError as e:
                print(" Could not create snapshot for instance {0}, volume {1}: {2}".format(i.id, v.id, str(e)))
                needRestart = False
                continue

        if needRestart:
            print("Startng {0}...".format(i.id))
            i.start()
            i.wait_until_running()
            needRestart = False
        else:
            print("{0} will stay in {1} status.  Snapshot complete".format(i.id, i.state['Name']))

    print("Job is done")

    return

@instances.command('list')
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--instance', 'my_i', default=None,
    help="List only the specified instance")
def list_instances(project, my_i):
    "List EC2 instances"

    instances = filter_instances(project, my_i)

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
@click.option('--instance','my_id', default=None,
    help="Only the specified id")
def reboot_instances(project, enforcer, my_id):
    "Reboot EC2 instances"

    instances = filter_instances3(project, enforcer, my_id)

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
@click.option('--instance','my_id', default=None,
    help="Only specified instance")
def stop_instances(project, enforcer, my_id):
    "Stop EC2 instances"

    instances = filter_instances3(project, enforcer, my_id)

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
@click.option('--instance', 'my_id', default=None,
    help="Only specified instance")
def start_instances(project, enforcer, my_id):
    "Start EC2 instances"

    instances = filter_instances3(project, enforcer, my_id)

    for i in instances:
        print ("Starting {0}".format(i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print(" Could not start {0}: {1}".format(i.id, str(e)))
            continue

if __name__ == '__main__':
    cli()
