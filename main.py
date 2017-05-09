#!/usr/bin/python
""".

Automation: Monitoring Disable
Author: Erik Horton

Prerequisites:
Clone repositories inside this directory.
    1. pyCAServiceDesk - https://github.com/hortonew/pyCAServiceDesk
    2. pyCAUIM - https://github.com/hortonew/pyCAUIM

Description:
    1. Finds all tickets for team
    2. Any tasks the are scheduled in the next 60m; schedule maintenance
"""
import os
from patterns import PATTERN_CUSTOMER_ROBOT, PATTERN_CUSTOMER_HUB, PATTERN_SITE
from pyCAServiceDesk import main as py_ca_servicedesk
from pyCAUIM import main as py_cauim
from dateutil import parser
from datetime import datetime
import logging
from logging.config import dictConfig

"""
Minutes it'll wait before scheduling a task's disable

Set to 60 means:
If task planned start is 0800, current time is 0700, don't run
If task planned start is 0800, current time is 0701, run
"""
MINUTES_BEFORE_SCHEDULING = 60

# Change to True when ready for real run
PRODUCTION = True
LOGLEVEL = logging.DEBUG

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
LOGFILE = "pyCATaskScheduler.log"
LOGPATH = os.path.join(CURRENT_DIR, "logs", LOGFILE)

# Log config
logging_config = {
    "version": 1,
    "formatters": {
        'f': {'format': '%(asctime)s level=%(levelname)s %(message)s'}
    },
    "handlers": {
        'h': {
            'class': 'logging.handlers.RotatingFileHandler', 
            'filename': LOGPATH, 
            'maxBytes': (1024 * 1024) * 2,
            'backupCount': 2,
            'formatter': 'f', 
            'level': LOGLEVEL}
    },
    "root": {'handlers': ['h'], 'level': LOGLEVEL}
}
logging.config.dictConfig(logging_config)

def identify_robot_details(robot):
    """Match company specific info to robot."""
    try:
        robot_customer = PATTERN_CUSTOMER_ROBOT.search(robot).group(1)
    except:
        robot_customer = "ROBOT_CUSTOMER_FAILED"
    try:
        robot_site = PATTERN_SITE.search(robot).group(1)
    except:
        robot_site = "ROBOT_SITE_FAILED"
    return robot_site, robot_customer


def identify_hub_details(hub):
    """Match company specific info to hub."""
    try:
        hub_site = PATTERN_SITE.search(hub).group(1)
    except:
        hub_site = "HUB_SITE_FAILED"

    # Figures out customer of hub
    try:
        hub_customer = PATTERN_CUSTOMER_HUB.search(hub).group(1)
    except:
        hub_customer = "HUB_CUSTOMER_FAILED"

    return hub_site, hub_customer


def identify_hub(robots):
    """Get hubs for a list of robots."""
    hubs = py_cauim.get_all_hubs()
    robots_and_hubs = dict()

    for robot in robots:
        robots_and_hubs[robot] = dict()
        robots_and_hubs[robot]["robotname"] = robot

        # Figures out site and customer of robot
        robot_site, robot_customer = identify_robot_details(robot)

        if (len(robot_site) != 0 and (len(robot_customer) != 0)):
            # Loop over hubs
            for hub in hubs:
                # Figures out site of hub
                hub_site, hub_customer = identify_hub_details(hub)
                if (hub_site == robot_site and hub_customer == robot_customer):
                    robots_and_hubs[robot]["found"] = True
                    robots_and_hubs[robot]["hubname"] = hub
        else:
            robots_and_hubs[robot]["found"] = False
            robots_and_hubs[robot]["hubname"] = "Undefined"

    return robots_and_hubs


def convert_datetime_to_epoch(dt):
    """Convert datetime format to epoch."""
    import time
    # Convert to int as mktime returns float
    return int(time.mktime(dt.timetuple()))


def schedule_maintenance_mode(ticket, server_list):
    """
    Schedule maintenance mode in CA UIM.

    Status: Development
    """
    # Make the list lowercase
    server_list = [x.lower() for x in server_list]
    rh = identify_hub(server_list)

    try:
        start_time = ticket["Planned Start Date"]
        end_time = ticket["Planned End Date"]
        dt_start = parser.parse(start_time)
        dt_end = parser.parse(end_time)
        start_time_epoch = convert_datetime_to_epoch(dt_start)
        end_time_epoch = convert_datetime_to_epoch(dt_end)
    except:
        print "Problem getting start/end times.  Inform ticket creator."
        return 1
    for server in server_list:
        current_time = str(datetime.now())
        hub = rh[server]["hubname"]
        rc = py_cauim.maintenance_mode(
            server, hub, start_time_epoch, end_time_epoch
        )
        print "Maintenance on " + server + " is " + str(rc)
        log = "id={0}, server={1}, start_time={2}, end_time={3}, start_time_epoch={4}, end_time_epoch={5}"\
                .format(ticket["id"], server, start_time, end_time, start_time_epoch, end_time_epoch)
        if (str(rc)=="<Response [200]>"):
            logging.info(log)
        else:
            logging.error(log)
    return 0


def should_schedule_maintenance(t):
    """Return true if within range to start."""
    try:
        dt = parser.parse(t["Planned Start Date"])
        change = convert_datetime_to_epoch(dt)
        now = convert_datetime_to_epoch(datetime.now().replace(second=0,microsecond=0))
        minutes_until_change = (change - now)/60
        if (minutes_until_change < MINUTES_BEFORE_SCHEDULING):
            print str(minutes_until_change) + " minutes until change.  \
                Scheduling..."
            log = "id={0}, planned_start_date={1}, minutes_until_change={2}, should_schedule=true"\
                .format(t["id"], t["Planned Start Date"], minutes_until_change)
            logging.debug(log)
            return True
        else:
            print str(minutes_until_change) + " minutes until change. "
            log = "id={0}, planned_start_date={1}, minutes_until_change={2}, should_schedule=false"\
                .format(t["id"], t["Planned Start Date"], minutes_until_change)
            logging.debug(log)
            return False
    except:
        print "No planned start/end time: " + t["id"]
        log = "id={0},should_schedule=false,has_start_end_times=false".format(t["id"])
        logging.error(log)
        return False


def process_ticket(ticket):
    """Process a single ticket, scheduling its maintenance period."""
    t = ticket
    status = {
        0: "Success",
        1: "Failure",
        2: "Not ready to be scheduled"
    }
    if PRODUCTION:
        #t = py_ca_servicedesk.get_ticket_information(ticket)
        if should_schedule_maintenance(t):
            s = py_ca_servicedesk.get_config_items_associated_with_ticket(t)
            return_code = schedule_maintenance_mode(t, s)
            print "PRODUCTION: " + t["id"] + " - " + status[return_code]
        else:
            print "PRODUCTION: " + t["id"] + " - " + status[2]
    else:
        print "DEVELOPMENT: " + t["id"] + " - " + status[0]


def process_all_tickets():
    """Process all tickets, scheduling their maintenance period."""
    tickets = py_ca_servicedesk.get_current_task_tickets()
    for ticket in tickets:
        process_ticket(ticket)


def process_all_disable_tickets():
    """Process all disable tickets, scheduling their maintenance period."""
    tickets = py_ca_servicedesk.get_current_task_tickets()
    for t in tickets:
        if (tickets[t]["Class"]=="Monitoring" and tickets[t]["Category"]=="Disable" and tickets[t]["id"]=="500-326101"):
            process_ticket(tickets[t])


if __name__ == "__main__":
    logging.debug("status=starting")
    py_ca_servicedesk.refresh_cache()
    process_all_disable_tickets()
    logging.debug("status=ending")

