## TODOs 

1. Assumptions in the excel processing
	- First row has column names 
	- "id" columns are the only ones containing lookup keys (take as input)
	- "." is a safe separator for joins (i.e it's not present in column names - take as input)


## Known issues 

1. Choosing 1 excel then another (without reload) results in a crash 

## Appendix 

### Background resizing 

* `q:v` higher is more compressed
* `scale` lower is fewer pixels 
```
$ ffmpeg -i background.png -vf scale=600:-1 -q:v 80 /tmp/background.webp
```
