# MMMHub-SAFE
MMMHub's SAFE integration tools

`safe_json_decoder.py` takes JSON output from SAFE and turns it into Python objects. We used objects to have some basic checking that all necessary fields were being set.

`safe_tickets_skeleton.py` is a skeleton example of how we use the decoder, with all the UCL-specific implementation details removed. In the places it does nothing useful it has comments stating what we do there.

## Config file

All connections take place from `safe_tickets_skeleton.py` and assume the user running it has a `~/.safe.cnf` with all necessary connection info and credentials.

We keep a database with user information and it includes a table where we put SAFE tickets before acting on them.

The config file should be of this form, with `local_database` being our SQL database details and `safe` being the connection details for the SAFE. The `gold` address we have in there allows us to do budget management inside SAFE - your SAFE setup may vary. We keep the canonical budget values locally (managed by Gold) and update the SAFE values regularly.

```
[local_database]
user=myusername
password=mypassword
host=database.host

[safe]
host=https://path/to/SysAdminServlet
user=mySAFEuser
password=mySAFEpassword
gold=https://path/to/ServiceMachineServlet
```
