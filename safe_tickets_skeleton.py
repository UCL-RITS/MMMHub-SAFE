#!/usr/bin/env python3

# This is a skeleton example of how we use the SAFE ticket parser.
# You'll need to make the ticket-handling methods do something useful 
# instead of print statements.

# We put SAFE tickets into a SQL database before acting on them; this is
# what "DB" is referring to. safetickets is one table in our user database.

import os.path
import sys
import configparser
import argparse
import subprocess
import mysql.connector
from mysql.connector import errorcode
import json
import requests
# this is our safe_json_decoder.py
import safe_json_decoder as decoder

def getargs(argv):
    parser = argparse.ArgumentParser(description="Show, refresh or update and close tickets from SAFE.")
    parser.add_argument("-s", "--show", dest="show", help="Show all open tickets in SAFE", action='store_true')
    parser.add_argument("-f", "--file", dest="jsonfile", default=None, help="Parse json tickets from a file (parser test)")
    parser.add_argument("-r", "--refresh", dest="refresh", help="Refresh open tickets in DB from SAFE and display them", action='store_true')
    parser.add_argument("-c", "--close", dest="close", default=None, help="Carry out and close this ticket ID")
    parser.add_argument("--reject", dest="reject", default=None, help="Reject this ticket ID")
    parser.add_argument("--debug", help="Show what would be submitted without committing the change", action='store_true')

    # Show the usage if no arguments are supplied
    if len(argv) < 1:
        parser.print_usage()
        exit(1)

    # return the arguments
    # contains only the attributes for the main parser and the subparser that was used
    return parser.parse_args(argv)
# end getargs

def parsejsonfile(filename):
    f = open(filename, 'r')
    jdata = f.read()
    ticketlist = decoder.JSONtoTickets(jdata)
    f.close()
    for t in ticketlist:
        print(str(t.Ticket))
    print("Number of tickets included: " + str(len(ticketlist)))

# Connect to SAFE, get open tickets as JSON
def getopentickets(config):
    request = requests.get(config['safe']['host'] + "?mode=json", auth = (config['safe']['user'], config['safe']['password']))
    if request.status_code == 200:
        try:
            data = request.json()
            return data
        except json.decoder.JSONDecodeError as err:
            print("Received invalid json, contents: " + str(request.content))
            exit(1)
    else:
        print("Request not successful, code " + str(request.status_code))

# end getopentickets

# Get a decoded list of tickets
def gettickets(config):
        # get SAFE tickets
        jsontickets = getopentickets(config)
        # parse SAFE tickets
        ticketlist = decoder.JSONDataToTickets(jsontickets)
        return ticketlist
# end gettickets


# SAFE has some parameters that must be supplied when completing
# or rejecting tickets: these set those parameters.

# Update and complete a budget (project) ticket
def updatebudget(ticket_id, projectname):
    parameters = {'qtid':ticket_id, 'new_username':projectname, 'mode':'completed'}
    return parameters

# Update any type of ticket that just needs to be told it is complete
def updategeneric(ticket_id):
    parameters = {'qtid':ticket_id, 'mode':'completed'}
    return parameters

def updateaddtobudget(ticket_id):
    parameters = {'qtid':ticket_id, 'mode':'completed'}
    return parameters

# Update and complete a New User ticket
def updatenewuser(ticket_id, username):
    parameters = {'qtid':ticket_id, 'new_username':username, 'mode':'completed'}
    return parameters

# Reject the ticket because it would cause an error
def rejecterror(ticket_id):
    parameters = {'qtid':ticket_id, 'mode':'error'}
    return parameters

# Reject the ticket for any other reason
def rejectother(ticket_id):
    parameters = {'qtid':ticket_id, 'mode':'refused'}
    return parameters


# Update and close a ticket.
# parameters is a dictionary of values: {'qtid':id,'new_username':'Test', 'mode':'completed'}
def updateticket(config, args, parameters):
    if args.debug:
        print("Post request would be to " + config['safe']['host'] + " with params = " + str(parameters))
    else:
        request = requests.post(config['safe']['host'], auth = (config['safe']['user'], config['safe']['password']), params = parameters)
        if "<title>SysAdminServlet Success</title>" in request.text:
            print("Ticket " + parameters['qtid'] + " closed.")
# end updateticket


# Deal with a New User ticket
def newuser(cursor, config, args, ticketid):

    # Things we do here:
    #  * Get this ticket ID from our DB, inc all the needed fields
    #  * Find or allocate their username
    #  * Check we are running this request on the correct cluster!

    print("Ticket ID " + ticketid + " was identified as a New User ticket.")

    # update SAFE and close the ticket
    updateticket(config, args, updatenewuser(ticketid, user_dict['username']))

    # Then update ticket status in our DB

# end newuser


# Deal with a New Budget ticket
def newbudget(cursor, config, args, ticketid):

    # Things we do here:
    #  * Get this ticket ID from our DB, inc all the needed fields
    #  * Work out which institute this budget belongs to (by naming scheme)
    #  * Add the new budget to our database

    print("Ticket ID " + ticketid + " was identified as a New Budget ticket.")

    # update SAFE and close the ticket
    updateticket(config, args, updatebudget(ticketid, projectname))

    # Then update ticket status in our DB

# end newbudget


# Deal with an Add to budget ticket
def addtobudget(cursor, config, args, ticketid):

    # Things we do here:
    #  * Get this ticket ID from our DB, inc all the needed fields
    #  * This is an existing budget: get the point of contact ID
    #  * Add a 'projectuser' to our DB (username:budget pairing)

    print("Ticket ID " + ticketid + " was identified as an Add to budget ticket.")

    # update SAFE and close the ticket
    updateticket(config, args, updategeneric(ticketid))

    # Then update ticket status in our DB

# end addtobudget


# New User and Add to budget tickets come in pairs.
# Match a New User ticket with an Add to budget ticket for the same user
def matchbudgetticket(cursor, ticketid):

    # Things we do here:
    #  * Get the username from the New User ticket in our DB
    #  * Find the first matching Add to budget ticket for that username
    #  * Deal with case where there are no matches (either did it already or need refresh)

    print("Ticket ID " + ticketid + " should have a matching Add to budget ticket.")

    # Return the ticket ID of the Add to budget ticket

# end matchbudgetticket


# Deal with an Update account ticket. ExtraText should contain info about what to update.
def updateaccount(cursor, config, args, ticketid):

    # Things we do here:
    # * Get this ticket ID from our DB, inc all the needed fields
    # * The case we currently know about is "public key added" - do that
    # * Exit with error on cases we don't know how to handle

    print("Ticket ID " + ticketid + " was identified as an Update account ticket.")

    # update SAFE and close the ticket
    updateticket(config, args, updategeneric(ticketid))

    # Then update ticket status in our DB

# end updateaccount


# Deal with a Move gold ticket
# This is customised so we receive SourceAccountID, SourceAllocation, Amount, Project
# which is everything we need to do the transfer.
def movegold(cursor, config, args, ticketid):

    # Things we do here:
    #  * Get this ticket ID from our DB, inc all the needed fields
    #  * Run our local transfergold command

    print("Ticket ID " + ticketid + " was identified as a Move gold ticket.")

    # update SAFE and close the ticket
    updateticket(config, args, updategeneric(ticketid))

    # Then update ticket status in our DB

# end movegold


# Turn a list of tickets into a list of dicts for use in SQL queries
def ticketstodicts(ticketlist):
    ticket_dicts = []
    for t in ticketlist:
        t_dict = {
                       "id": t.Ticket.Id,
                       "type": t.Ticket.Type,
                       "status": t.Ticket.Status,
                       "account_name": t.Ticket.Account.Name,
                       "machine": t.Ticket.Machine,
                       "project": t.Ticket.ProjectGroup.Code,
                       "firstname": t.Ticket.Account.Person.FirstName,
                       "lastname": t.Ticket.Account.Person.LastName,
                       "email": t.Ticket.Account.Person.Email,
                       "publickey": t.Ticket.Account.Person.NormalisedPublicKey,
                       "poc_firstname": t.Ticket.Approver.FirstName,
                       "poc_lastname": t.Ticket.Approver.LastName,
                       "poc_email": t.Ticket.Approver.Email,
                       "source_account_id": t.Ticket.GoldTransfer.SourceAccountID,
                       "source_allocation": t.Ticket.GoldTransfer.SourceAllocation,
                       "gold_amount": t.Ticket.GoldTransfer.Amount,
                       "extratext": t.Ticket.ExtraText,
                       "startdate": t.Ticket.StartDate,
                       "enddate": t.Ticket.EndDate
                 }
        ticket_dicts.append(t_dict)
    return ticket_dicts


# Put main in a function so it is importable.
def main(argv):

    try:
        args = getargs(argv)
        # make a dictionary from args to make string substitutions doable by key name
        args_dict = vars(args)
    except ValueError as err:
        print(err)
        exit(1)
    try:
        # This file contains all necessary configuration for SQL connector and HTTPS requests
        config = configparser.ConfigParser()
        config.read_file(open(os.path.expanduser('~/.safe.cnf')))
    #except FileNotFoundError as err:
    except OSError as err:
        print(err)

    # Basic test: read tickets from a file
    if args.jsonfile is not None:
        parsejsonfile(args.jsonfile)

    # Show tickets live from SAFE
    if args.show:
        # get SAFE tickets
        ticketlist = gettickets(config)

        # print SAFE tickets
        for t in ticketlist:
            values = [t.Ticket.Id, t.Ticket.Type, t.Ticket.Status, t.Ticket.Account.Name, t.Ticket.Machine, t.Ticket.ProjectGroup.Code, t.Ticket.Account.Person.FirstName, t.Ticket.Account.Person.LastName, t.Ticket.Account.Person.Email, t.Ticket.Account.Person.NormalisedPublicKey, t.Ticket.Approver.FirstName, t.Ticket.Approver.LastName, t.Ticket.Approver.Email, t.Ticket.GoldTransfer.SourceAccountID, t.Ticket.GoldTransfer.SourceAllocation, t.Ticket.GoldTransfer.Amount, t.Ticket.ExtraText, t.Ticket.StartDate, t.Ticket.EndDate]
            print(values)
        print("Number of pending tickets: " + str(len(ticketlist)))

    # These options require a database connection
    if args.refresh or args.close is not None or args.reject is not None:
        try:
            conn = mysql.connector.connect(option_files=os.path.expanduser('~/.safe.cnf'), option_groups='local_database', database='tier2')
            cursor = conn.cursor(dictionary=True)

            # Refresh the database tickets
            if args.refresh:
                # get SAFE tickets as list of dicts
                ticketdicts = ticketstodicts(gettickets(config))
                # refresh tickets in database
                for t in ticketdicts:
                    # Things we do here:
                    # * Run a DB query to refresh the tickets 
                    print ("Refreshing ticket")
                # show database tickets (not inc ssh key)
                print("Refreshed tickets:")
                # Things we do here:
                # * Run a DB query to get all the pending tickets
                # * Print them out as a table
                
            # Update and close SAFE tickets
            if args.close is not None:
                # for readability in query
                ticket = args.close
                # Things we do here:
                # * Run a DB query to get the ticket type
                # * Exit if there are no tickets found with the given ID

                print("Ticket ID " + ticket + " found.")

                # This should be set from the above query
                tickettype = "Test"

                # Store all the ticket info, dependent on type

                # new user
                if tickettype == "New User":
                    newuser(cursor, config, args, ticket)
                    # Each new user ticket should have a matching Add to budget ticket.
                    # Find it if it exists and complete it too.
                    match = matchbudgetticket(cursor, ticket)
                    if match is not None:
                        print("Matching 'Add to budget' ticket " + str(match['ticket_ID'])  +  " found for this new user, carrying out.")
                        addtobudget(cursor, config, args, match['ticket_ID'])

                # new budget
                elif tickettype == "New Budget":
                    newbudget(cursor, config, args, ticket)
                # add to budget
                elif tickettype == "Add to budget":
                    addtobudget(cursor, config, args, ticket)
                # update account info
                elif tickettype == "Update account":
                    updateaccount(cursor, config, args, ticket)
                # move Gold and refresh SAFE
                elif tickettype == "Move gold":
                    movegold(cursor, config, args, ticket)
                    # Also run command to push current Gold values back to SAFE
                else:
                    print("Ticket " + ticket + " type unrecognised: " + tickettype)
                    exit(1)

            # Reject SAFE tickets - there are two types of rejection so ask
            if args.reject is not None:
                ticket = args.reject
                # Things we do here:
                # * Accept "other" or "error" as rejection reason
                # answer should be set using that response.
                answer = "other"
                if answer == "error":
                    updateticket(config, args, rejecterror(ticket))
                    # Then update ticket status in our DB

                else:
                    updateticket(config, args, rejectother(ticket))
                    # Then update ticket status in our DB

            # commit the change to the database unless we are debugging
            if not args.debug:
                conn.commit()

        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Access denied: Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)
        else:
            cursor.close()
            conn.close()
# end main

# When not imported, use the normal global arguments
if __name__ == "__main__":
    main(sys.argv[1:])

