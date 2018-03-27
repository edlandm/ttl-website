import math

# Function to turn 1 into '1st', 2 into '2nd', 3 into '3rd, etc
# source: https://stackoverflow.com/questions/9647202/ordinal-numbers-replacement#20007730
ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])
