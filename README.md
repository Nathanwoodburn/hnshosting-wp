# HNSHosting Wordpress
This is split into two parts.
There is the master server which is the server that will be used to manage the worker servers.
Then there is the worker server which is the server that will be used to host the wordpress site.

This is done to make it easier to manage multiple wordpress sites on multiple servers.

## Master server install

Install prerequisites:

```
chmod +x install.sh
./install.sh
```

This will create the service to run the master server.


## Worker server install

Install prerequisites:

```
chmod +x install.sh
./install.sh
```