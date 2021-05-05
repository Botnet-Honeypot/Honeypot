# Botnet Honeypot

## Requirements
* Port 5432 is used for the database by default, needs to be open for the database machine.
* Port 22 is used on system(s) that runs the frontend(s), if the system provides an SSH-server it needs to be changed to another port or disabled. This port needs to be open for the frontend machine(s).
* Ports 49152-65535 (IANA unregistered ports) are used for communication between the frontend and backend, so these need to be open for the backend machine.

## Running the honeypot on one machine

### Configuration
Change the values in `/dev/docker-compose.yaml`, at minimum it is recommended to change the username and password for the database. 

### Running
Run the docker-compose.yaml in the `/dev` directory file using `docker-compose up -d` to start all modules of the honeypot together.

## Running each module on separate machines

### Configuration

#### On the host which will be running the database
Change the values in `/database/docker-compose.yaml`, at minimum it is recommended to change the username and password for the database. 

#### On the host which will be running the frontend
Change the values in `/frontend/docker-compose.yaml` to fit your needs. At the minimum, the database connection settings and backend address must be filled in:
* DB_HOSTNAME: IP address to the database host machine
* DB_DATABASE: Database that will be accessed in the database.
* DB_USERNAME: Database user name.
* DB_PASSWORD: Database password.
* BACKEND_ADDRESS: IP address to the backend host machine.

#### On the host which will be running the backend
Change the TARGET_SYSTEM_ADDRESS in `/backend/docker-compose.yaml` to the IP of the host machine that will be running the backend.

### Running

#### On the host which will be running the database
Run the docker-compose.yaml in the `/database` directory file using `docker-compose up -d` to start all modules of the honeypot together.

#### On the host which will be running the frontend
Run the docker-compose.yaml in the `/frontend` directory file using `docker-compose up -d` to start all modules of the honeypot together.

#### On the host which will be running the backend
Run the docker-compose.yaml in the `/backend` directory file using `docker-compose up -d` to start all modules of the honeypot together.

##### (optional) Trying to prevent DDoS and other attacks
Since this project implements a high interaction honeypot, the attackers gain access to the resources available to the backend host. 
Therefore, we provide a WIP script for limiting the bandwidth on the backend. The script is provided as-is and worked on Ubuntu Linux 18.04.
The script limits most outgoing traffic from the backend host to 10 Mbit/s, and traffic on ports 21, 22, 23, 25, 53, 110, 135, 137, 138, 139, 1433, and 1434 to 1kbit/s. The speeds are configurable in the script using variables.
It does not limit incoming traffic speed. It has not been tested while running the entire honeypot on a single host.
The script is placed in 

## Accessing the collected information
Connect, using your preferred utility, to the IP address of the database providing the user name, password and database name you configured previously.

For example, using psql: `psql <db_name> -h <ip_address> -U <db_user>` and then provide the password when prompted.

## Development

- [Python Setup](documentation/python_setup.md)
- [Documentation](https://botnet-honeypot.github.io/Honeypot/)
- [Testing](documentation/testing.md)
