1. Parse arguments to get port to run discovery protocol on

So we have something broadcasting on the discovery protocol, and
something else listening on a different thread on the same port? How
does that work?


##Questions:

2. How does the get command work? What if there are two files of the
   same name? Does the program keep a record of all files and diff them
   each time? How does it know who to get the files from?
3. Does the server only run `files?` when the user asks it to, or is it
   always pinging others asking for files, and keeping a list?
4. Shared data - what? a map of ZapFile objects that represent the file
   in blocks?
5. How does the UI communicate with the threads that are downloading
   stuff?
6. How does the broadcast know when more files are downloaded?
7. A command queue for communicating? Then the broadcast one sets up the
   TCP stuff. Hrrrrmmmmm.
8. For the TCP stuff, is everyone running a TCP server on their machine
   that spits out new sockets? WHAT DOES IT MEAN????? So i see a file i
   want, I request it with get [file], look up that file in the file
   list, find the ip address and port of the person with the file, and make
   however many sockets i want to download it? WUUUTT?
9. Remote files are stored uniquely by filename. When a user requests to
   download a file, 

##Answers
1. How does the load command work? Copy to a specific location? Or just
   add to an internal list? Add to an internal list for simplicity.
