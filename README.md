# persistedRmq
A simple MQ based on Redis pubsub, but won't lose message

## Installation

    pip install persistedRmq
    
## Usage

See example

    cd example
    pip install fastapi
    pip install persistedRmq
    uvicorn app:app --reload
    
Open Browser http://localhost:8000#clientA 
Open Another Browser http://localhost:8000#clientB

Enjoy!
   
### ver 0.0.2
1. add temporary message storage timeout.