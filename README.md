Virtal Botmaster
================

"Simulate Botnet NetFlow traffic for evaluating the boundaries of botnet detection methods"

The VirtualBotmaster is a program that generates new botnet flows in order to evaluate the boundaries of botnet detection methods.

It can generate network flows accordingly to the behavioral model of a Botmaster, the behavioral model of a botnet, the model of a bot and the behavioral model of the C&C channels. Its goal is to generate new flows that are based on real botnet traffic, but different enough that may not be detected by the detection method you are trying to evaluate. 

Each part of the VirtualBotmaster, i.e. the Botmaster, the Botnet, the Bot and the C&Cs has its own states and transitions between states that are defined accordingly to a model. The botmaster states are related to decisions about the actions to be done, the botnet states are related to the management of all the bots, the bots states are related to changes in its environment. The states of the C&C are the most complex because their are based on the real states of botnet C&C seen in the wild. The C&C module generates the flows accordingly to a Markov Chain-based model of the real behavior of a C&C. 

All the states transitions and parameters of the flows can be generalized to evaluate how a detection method reacts to these changes. For example, you can change the periodicity between flows, the sizes of the flows according to a distribution function, the amount of C&C, the type of C&C, etc.


Configuration
=============
All the configurations are in the VirtualBotmaster.conf file.
You can generalize every parameter from that file.


Example Usage
=============
./VirtualBotmaster.py -x 10000
