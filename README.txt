""".

Example patterns.py

Description:  The point of this file is to pre-build matching criteria.
All matches are company specific and may need to be modified.

PATTERN_CUSTOMER_ROBOT - Matches part of the robot name to determine the customer
PATTERN_CUSTOMER_HUB - Matches part of the hub name to determine customer

If PATTERN_CUSTOMER_ROBOT and PATTERN_CUSTOMER_HUB match, a robot is matched to a hub
however the PATTERN_SITE in both must also match.

Example:
robot = xxx-zzz-yyy-0001
hub1 = xxx-111-zzz-0001
hub2 = xxx-111-ddd-0001

PATTERN_CUSTOMER_ROBOT = re.compile("\w\w\w\-(\w\w\w)\-\w\w\w\-\d\d\d\d")
PATTERN_CUSTOMER_HUB = re.compile("\w\w\w\-\d\d\d\-(\w\w\w)\-\d\d\d\d")

Both of these would match robot to hub1, because the result would be "zzz".
Robot would not match hub2.

The next match would look at PATTERN_SITE
PATTERN_SITE = re.compile("^(\w\w\w)\-.+$")

Because both the robot and hub1 have "xxx" as the site, the final match would work.
All matching statements are found in the main program. 
"""
# Matches to find customer name and site for machine
# Match group is inside parenthese
import re
PATTERN_CUSTOMER_ROBOT = re.compile("\w\w\w\-(someMatchThatDeterminesCustomerInRobotName)")
PATTERN_CUSTOMER_HUB = re.compile("\w\w(someMatchThatDeterminesCustomerInHubName)")
PATTERN_SITE = re.compile("(someMatchThatDeterminesSiteIfYouHaveCustomerInMultipleSites)")
