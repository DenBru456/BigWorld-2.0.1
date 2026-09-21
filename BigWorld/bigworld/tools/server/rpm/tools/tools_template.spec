# ========== IMPORTANT ==========
# 
# DO NOT BUILD PACKAGES AS ROOT USER!!!!!!
#
# Doing so may damage the system (i.e. render the system unusable) if 
# the RPM spec file contains error, since the error may delete system 
# files.



# Macros. 
%define bigworld_dir			/opt/bigworld/%{bw_version}
%define bigworld_current_dir	/opt/bigworld/current

%define name					bigworld-tools
%define bigworld_tools_dir		%{bigworld_dir}/tools
%define bigworld_initrd_dir		%{bigworld_tools_dir}/init.d
%define bigworld_conf_dir		%{_sysconfdir}/bigworld
%define message_logger_dir		/var/log/bigworld/message_logger
%define daemon_log_dir			/var/log/bigworld
%define pid_dir					/var/run/bigworld
%define sqlite_db_dir			/var/lib/bigworld
%define cron_hourly_dir			/etc/cron.hourly
%define logrotate_dir			/etc/logrotate.d
%define bw_tools_user			bwtools
%define services				bw_lockd bw_message_logger bw_web_console
## PLACEHOLDER: PACKAGE SPECIFIC MACROS 


Name:		%{name}
Version:	%{bw_version}.%{bw_patch}
Release:	%{bw_patch}.%{bw_svn_rev}
Group:		Middleware/MMOG
Vendor:		BigWorld Pty Ltd
URL:		http://www.bigworldtech.com/
Packager:	BigWorld Support <support@bigworldtech.com>
License:	BigWorld License
Summary:	The BigWorld server tools.
## ExcludeArch: <arch1>, <arch2>, ..., <archN>
ExclusiveArch: x86_64
## Excludeos: <os1>, <os2>, ..., <osN>
Exclusiveos: linux
## The next line is used for generating the actual BuildRoot line from script
## please do not remove it.
## PLACEHOLDER: BUILDROOT
Provides: bigworld-tools-%{bw_version}
Requires(pre):  /sbin/service, /sbin/chkconfig, /usr/bin/id
Requires(post): /sbin/service, /sbin/chkconfig
Requires: bigworld-bwmachined, epel-release, TurboGears, wxPython
## Obsoletes:
## Conflicts:


%description
This package contains the Server Tools component of the BigWorld Server. This
includes WebConsole and MessageLogger. 


# This is pre-install script.
%pre 

for service in %{services}; do
	if test -f %{_initrddir}/$service; then
		/sbin/service $service stop > /dev/null 2>&1
		/sbin/chkconfig --del $service
	fi
done

if ! id %{bw_tools_user} > /dev/null 2>&1; then
	adduser -r %{bw_tools_user}
fi



# This is post-install script. 
%post

# All the directories required to write into for the tools
for dir in %{daemon_log_dir} %{pid_dir} %{message_logger_dir} %{sqlite_db_dir}; do
	if ! test -d $dir; then
		mkdir -p $dir
	fi
	chown -R %{bw_tools_user}:%{bw_tools_user} $dir
done


# Set the SELinux security context before starting any services that might
# use the file.
if [ -f /usr/sbin/selinuxenabled ]; then

	# Run the command and check the return status (0 == enabled, 1 == disabled)
	/usr/sbin/selinuxenabled
	if [ $? == 0 ]; then
		chcon -t textrel_shlib_t %{bigworld_tools_dir}/bin/%{mf_config}/bwlog.so
	fi
fi


# Add and start the services
for service in %{services}; do
	/sbin/chkconfig --add $service
	/sbin/service $service start
done


su -c "/sbin/service bw_message_logger logrotate" %{bw_tools_user} > /dev/null 2>&1 || true
# su -c "/sbin/service bw_stat_logger logrotate" > /dev/null 2>&1 || true
su -c "/sbin/service bw_web_console logrotate" > /dev/null 2>&1 || true


# This is pre-uninstall script.
%preun 


# Only run this when the software is being uninstalled, rather than
# upgraded/updated. $1 is an argument passed to script automatically 
# which stores the count of version of the software installed after
# the installation or uninstall. 
if [ "$1" -eq 0 ]; then
	for service in %{services}; do
		/sbin/service $service stop > /dev/null 2>&1
		/sbin/chkconfig --del $service
	done
fi

# Files to include in binary RPM.
%files 

## PLACEHOLDER: FILES FOR RPM


%changelog
* Tue Aug 08 2008 BigWorld Support
- Version 1.0.


