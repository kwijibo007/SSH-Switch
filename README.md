# SSH-Switch
An IndigoDomo plugin to Enable/Disable SSH on Mac OS 

SSH Switch is a simple plugin which allows you to enable/disable SSH (Remote Login) on the Mac running Indigo server. The ability to enable/disable SSH is presented as a standard Indigo switch.

In addition to SSH control, the plugin can also report your public IP address and the date it was last updated.

Please note: In order to allow the plugin to enable/disable SSH (Remote Login), a change to your Mac's sudoers file is required. This change grants the user running indigo the permission to query the state of SSH, turn SSH on and turn SSH off without entering an administrator password. 

Using visudo, edit the sudoers file by adding the folling lines to the "User privilege specification" section. Replace "my_username" with the user running Indigo Server.

my_username    ALL=(ALL) NOPASSWD: /usr/sbin/systemsetup -getremotelogin

my_username    ALL=(ALL) NOPASSWD: /usr/sbin/systemsetup -setremotelogin on

my_username    ALL=(ALL) NOPASSWD: /usr/sbin/systemsetup -f -setremotelogin off
