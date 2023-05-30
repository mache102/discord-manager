# discord-manager 
Application manager for GuildRock SMP    
**!!WIP README!!**  

## Setup
Start by installing `requirements.txt`.  

Enter your credentials & discord info in `config.yaml`

## App Management

### Starting an app

Copy the first message of the application & paste to `APPLICATION_LINK` in `config.yaml`.  
Set an appropriate nickname for the applicant in `APPLICANT_NAME`. This will be used in thread creation and appear in application metadata.  
  
Start the application:
```
python3 main.py -act start
```

### Closing an app

Close the ongoing application as follows:  

```
python3 main.py -act end -result [decision]-[mtype]
```
Where `[decision]-[mtype]` is a valid option in `result_options.ini`.

### Sending a standalone result message

For applications without the need to start a vote process, send a result message as follows:  
```
python3 main.py -act result_only -result [decision]-[mtype]
```
