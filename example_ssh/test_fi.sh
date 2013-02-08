#!/usr/bin/expect -f

set timeout 60 
spawn lli -load=/usr/lib/libcrypto.so -load=/usr/lib/libdl.so -load=/usr/lib/libutil.so -load=/usr/lib/libz.so -load=/usr/lib/libnsl.so -load=/usr/lib/libcrypt.so -load=/usr/lib/libresolv.so ssh.final_inject.bs.bc qining@ssh.ece.ubc.ca

expect {
	"password:"	{send "900928Lqn\r"}
	"ssh-linux"	{send "exit\r"}
}

expect {
	"ssh-linux"	{send "ls\r"}
}

expect {
	"ssh-linux"	{send "exit\r"}
}

while {1} {
	expect {
		"logout"	{break}
	}
}
