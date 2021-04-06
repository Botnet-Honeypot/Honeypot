#!/bin/bash

# Start decoy processes
# These are just processes that are named after common services
perl -wle '$0=shift;sleep shift' usr/bin/pihole-FTL 100000 &
perl -wle '$0=shift;sleep shift' /sbin/init 100000 &
perl -wle '$0=shift;sleep shift' /usr/sbin/lighttpd 100000 &
perl -wle '$0=shift;sleep shift' /etc/lighttpd/lighttpd.conf 100000 &
perl -wle '$0=shift;sleep shift' amarokapp 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/snapd/snapd 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/snapd/snapd 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/snapd/snapd 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/snapd/snapd 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/snapd/snapd 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/snapd/snapd 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/snapd/snapd 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/snapd/snapd 100000 &
perl -wle '$0=shift;sleep shift' /lib/systemd/systemd-logind 100000 &
perl -wle '$0=shift;sleep shift' /lib/systemd/systemd-journald 100000 &
perl -wle '$0=shift;sleep shift' /lib/systemd/systemd-udevd 100000 &
perl -wle '$0=shift;sleep shift' snapfuse /var/lib/snapd/snaps/ 100000 &
perl -wle '$0=shift;sleep shift' snapfuse /var/lib/snapd/snaps/ 100000 &
perl -wle '$0=shift;sleep shift' snapfuse /var/lib/snapd/snaps/ 100000 &
perl -wle '$0=shift;sleep shift' /usr/sbin/atd -f 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/php-cgi 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/php-cgi 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/php-cgi 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/php-cgi 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/policykit-l/plkitd 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/policykit-l/plkitd 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/policykit-l/plkitd 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/python3 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/python3 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/python3 100000 &
perl -wle '$0=shift;sleep shift' ssh:/usr/sbin/sshd 100000 &
perl -wle '$0=shift;sleep shift' ssh:/usr/sbin/sshd 100000 &
perl -wle '$0=shift;sleep shift' /usr/sbin/irqbalance 100000 &
perl -wle '$0=shift;sleep shift' /usr/sbin/NetworkManager 100000 &
perl -wle '$0=shift;sleep shift' /usr/lib/accountsservice/accounts-daemon 100000 &
perl -wle '$0=shift;sleep shift' /usr/sbin/ModemManager 100000 &
perl -wle '$0=shift;sleep shift' /usr/sbin/dnsmasq 100000 &
perl -wle '$0=shift;sleep shift' /usr/sbin/uuidd 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/perl 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/perl 100000 &
perl -wle '$0=shift;sleep shift' /usr/bin/perl 100000 &
perl -wle '$0=shift;sleep shift' npviewer.bin 100000 &
perl -wle '$0=shift;sleep shift' dbus-daemon 100000 &
perl -wle '$0=shift;sleep shift' netspeed_apple 100000 &

# Set up home directory
mkdir /home/$USER_NAME/ 
chown -R $USER_NAME /home/$USER_NAME
chmod -R 777 /home/$USER_NAME/

# Update home directory path in passwd file 
sed -i "s/\/config/\/home\/$USER_NAME/" "/etc/passwd" 
# Remove setup files
rm -rf /docker-mods

# Remove setup files
rm -rf /home/templatefiles
rm -rf /config/custom-cont-init.d
