# otree-redwood
`otree-redwood` is a library that enables oTree experiments to use websockets. An oTree page might collect one decision per player on the order of one minute. With websockets, player decisions can be collected and broadcast to other players in the group within tens of milliseconds without leaving the current page.

otree-redwood includes two parts:
* Server-side Python modules let the experimenter control how player input is collected and broadcast amongst a group.
* Client-side Javascript modules to integrate websocket events into existing user interfaces.

LEEPS Lab has used otree-redwood to create [several experiments](https://github.com/Leeps-Lab/otree-redwood/wiki/examples)

For more information including installation and usage instructions, check out the [wiki](https://github.com/Leeps-Lab/otree-redwood/wiki).
