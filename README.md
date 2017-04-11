###  extended Behavior Tree from the RVMI lab, Aalborg University Copenhagen, Denmark

Developer: Francesco Rovida  
License: BSD  
Last update: 10/04/2017  

**Compatibility**: Has been tested with Ubuntu 14.04 and Python 2.7

**extended Behavior Tree** is an extention of the standard Behavior Tree model to integrate scripted and planned procedures, with a direct applicability for robot task management.

It is possible to executing a demo running **main.py**. The demo gives an example on how the expansion and optimization of a sequence of skills works, by printing out in text format the standard expansion, and the optimize expansion. 

The skill set is defined in the **data/skill.py** file. 
The base ontology is defined in the **data/base_ontology.owl** file. (You can use the open-source app Protege to visualize it)

**Note**: for simplicity this package doesn't have the interfaces with the SkiROS package (https://github.com/frovida/skiros). World model and planned sequence are defined in code

### Dependencies
* rdflib  
* semanticnet   

### Install
* pip install rdflib
* pip install semanticnet

### Execute
Run in a terminal:
  python main.py

In the folder **results/** you can find the output file with (i) the initial scene, (ii) the initial eBT and (iii) the optimized eBT.

You can toggle the output verbosity by changing line 17 from verbose=False to verbose=True
