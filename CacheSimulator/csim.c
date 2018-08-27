/*
 Jonathan Saunders
 458332
 CacheLab
 */

#include "cachelab.h"
#include <stdio.h>
#include <getopt.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>

int _hits = 0;
int _misses = 0;
int _evictions = 0;
int _s; //number of set index bits
int _b; //number of block bits
int _E; //lines per set
char * _fileName;
unsigned long long _lru_Counter = 1;

/*
 Discussed my structs with Matt Gleeson (who was finished)
 before beginning so I didn't wreck myself going in 
 the wrong direction. Was given a "sounds good, I used a 2d array"
 
 The following struct stores information
 for any line within our cache system.
 is primary data that we are working with
 */
struct activeLine{
	unsigned long long recentlyUsed;
	unsigned long long tag;
	int valid;
};
typedef struct activeLine activeLine;

/*
 The next two structs basically act as 2D arrays
 to store all of our data in an easier to refer to way.
 
 Cache is simply used to hold array of all sets
 Each set has an array of lines and an int isFull
 This is for a little speed optimization later,
 Although we lose 4 bytes per Set due to alignment
 
 We also initialize a global cache object (currentCache)
 for use later.
 */

struct activeSet{
	activeLine *lineBegin;
	int isFull;
};
typedef struct activeSet activeSet;

struct cache{
	activeSet *startingSet;
} currentCache;

/*
 This function sets all of our user provided globals
 Returns 0 for exits correctly (no invalid supplied)
 Returns -1 for improper use
 Returns 1 for -h flag
 */
 
int initializeGlobals(int argc, char **argv){
	int opt;	
	//essentially "while I can still grab one of these arguments)
	//based on example at https://stackoverflow.com/questions/17877368/getopt-passing-string-parameter-for-argument
	//and example at https://stackoverflow.com/questions/4796662/how-to-take-integers-as-command-line-arguments
	while( ( opt = getopt(argc, argv, "s:E:b:t:h::") ) != -1 ){
		switch(opt){
			
			case 'h':
				return(1);
			
			case 'E':
				_E = atoi(optarg);
				break;
			
			case 's':
				_s = atoi(optarg);
				break;
			
			case 'b':
				_b = atoi(optarg);
				break;
			
			case 't':
				_fileName = optarg;
				break;
			
			default:
				return(-1);
		}
	}
	return 0;
}

/*
 This function does further argument checking
 It ensures that all our user specified parameters are actually set
 Returns 0 on success
 Returns 1 on error in values
 */
int checkArguments(){
	if( (!_s) ||(!_b) ||(!_E) || (!_fileName)){
		return 1;
	}
	if( _s < 0 ){ return 1; }
	if( _E < 1 ){ return 1; }
	if( _b < 0 ){ return 1; }
	return 0;
}

/*
 This function initializes our cache and allocates a dynamic amount of storage
 based on the user specified parameters.
 
 I originally was trying to use activeSet* currSet = currentCache.startingSet + sizeof(acitveSet)*i, etc...
 and was very confused when I was segfaulting later on in code. Much searching found that adding an 
 int n to a pointer implicity adds sizeof(object) * n... thanks compiler...
 */
void initializeCache(){
	
	int s = _s;
	int E = _E;
	
	//number of sets is 2^s so left shift binary 1 by s
	int numSets = (1 << s);
	
	currentCache.startingSet = (activeSet *) malloc( sizeof(activeSet) * numSets);
	
	//for each set
	for(int i = 0; i < numSets; ++i){
		
		//can use (activeSet *) + index as compiler deals with pointer math for us
		activeSet* currSet = currentCache.startingSet + i;
		
		(*currSet).lineBegin = (activeLine *) malloc( sizeof(activeLine) * E);
		(*currSet).isFull = 0;
		
		//for each line in that set
		for(int j = 0; j < E; j++){
			
			activeLine* currLine = (*currSet).lineBegin + j;
			
			(*currLine).valid = 0;
			(*currLine).recentlyUsed = 0;
			(*currLine).tag = 0;
		}
	}
	return;
}

/*
 Places object in cache at set index and sets activeLine.recentlyUsed. 
 Is only function that should increment lru_Counter of cacheProperties
 */

void placeCache(unsigned long long setIndex, unsigned long long tag, int lineIndex){
	
	activeSet * currSet = currentCache.startingSet + setIndex;
	activeLine* currLine = (*currSet).lineBegin + lineIndex;
	unsigned long long currentCount = _lru_Counter;
	
	(*currLine).valid = 1;
	(*currLine).recentlyUsed = currentCount;
	(*currLine).tag = tag;
	
	//incrementing the counter is important... lesson learned
	_lru_Counter++;
	return;
}

 /*
 This function  returns the line Index of some tag  
 in a set if it exists otherwise it returns -1
 */

int checkHit(unsigned long long setIndex, unsigned long long tag){
	
	activeSet * currSet = currentCache.startingSet + setIndex;
	unsigned long long currTag;
	int currValid;
	
	//for every line in the set
	for(int i = 0; i < _E; ++i){		
		activeLine* currLine = (*currSet).lineBegin + i;
		currTag = (*currLine).tag;
		currValid = (*currLine).valid;
		//if it is valid and the tag matches
		if(tag == currTag && currValid != 0){
			return i;
		}
	}
	return (-1);
}

 /*
  This function checks if the miss was cold or not, returns 
  line number of free line or -1 if there was a conflict.
 */
 
int checkCold(unsigned long long setIndex){
	activeSet * currSet = currentCache.startingSet + setIndex;
	int isFull = (*currSet).isFull;
	
	if(isFull){ return (-1); }
	
	for(int i = 0; i < _E; ++i){
		int currValid;
		activeLine* currLine = (*currSet).lineBegin + i;
		currValid = (*currLine).valid;
		if(currValid == 0){
			return i; 
		}
	}
	//if we exit the loop then we have filled our set
	(*currSet).isFull = 1;
	return (-1);
}

 /*
  This function finds the least recently used of some set and returns its line number
 */
 
int checkEvict(unsigned long long setIndex){
	
	activeSet * currSet = currentCache.startingSet + setIndex;
	unsigned long long lastUsed = 0;
	int returnLine;
	
	//for each line
	for(int i = 0; i < _E; ++i){
		activeLine* currLine = (*currSet).lineBegin +  i;
		unsigned long long currLastUsed = (*currLine).recentlyUsed;
		
		//if it is first line or the current line was used longer time ago
		if(!lastUsed || currLastUsed < lastUsed){ 
			returnLine = i;
			lastUsed = currLastUsed;
		}
	}

	return returnLine;
}

/*
 runs each address through the cache to see if hit or miss
 Uses unsigned long long for addresses juuuuust in case 
 there is a 1 in the top address bit
 */
void runCache(unsigned long long address){
	
	unsigned long long setIndex;
	unsigned long long tag;
	unsigned long long setMask;
	unsigned long long tmp = address;
	int hitLine;
	int setBits = _s;
	int blockBits = _b;
	int indexBits = setBits + blockBits; 
	
	//generates mask of lower (indexBits)
	setMask = ((1 << indexBits) - 1);
	
	//mask address and slam out the block index bits
	//use tmp for setIndex to prevent weird errors that 
	//I don't know why they were occurring during assigning tag
	setIndex = (tmp & setMask) >> (blockBits);
	
	tag = address >> (indexBits);

	hitLine = checkHit(setIndex, tag);
	
	//check if hits
	if(hitLine != -1){
		_hits += 1;
		//have to call place to update LRU counter, could just increment but consistency is nice
		placeCache(setIndex, tag, hitLine);
		return;
	}
	//otherwise we missed
	else{
		int coldLine;
		coldLine = checkCold(setIndex);
		_misses += 1;
		//if it was a cold miss just place it
		if(coldLine != -1){
			placeCache(setIndex, tag, coldLine);
			return;
		}
		//otherwise we have to evict a line
		else{
			int evictLine;
			evictLine = checkEvict(setIndex);
			placeCache(setIndex, tag, evictLine);
			_evictions += 1;
			return;
		}
	}
}
	
/*
 Parses file lines using fget and sscanf
 Passes the addresses of all non-I operations to be simulated
 Any M operations get simulated twice
*/

void runFileLines(){
	
	char line[127];
	const char * fileName;
	long long address;
	char optionType;
	
	fileName = _fileName;
	FILE* traceFile = fopen(fileName, "r");
	

	
	/*for every line in the file
	 put it in our char buffer line
	 file reading method courtesy of https://cboard.cprogramming.com/c-programming/137246-help-reading-file-c-fgets-sscanf.html:
	*/
	while( fgets(line, sizeof(line), traceFile) ){
		
		//we only need the type of operation and address
		//Piazza citation: https://piazza.com/class/jcgitxszcqf412?cid=226
		sscanf(line, "%s %llx", &optionType, &address);
		
		if(optionType == 'I'){
			//go to next line
			continue;
		}
		
		//do cache operation
		runCache(address);
		
		if(optionType == 'M'){
			//do cache operation additional time for m
			runCache(address);
		}
	}
	
	return;
}

/*
 Generates a helpful message for the user
 */
void usageMessage(char **argv){
	printf("Usage: %s [-hv] -s <num> -E <num> -b <num> -t <file> \n", argv[0]);
	printf("Options: \n");
	printf("  -h  \t\t Print this help message \n");
	printf("  -v  \t\t Optional verbose flag (not implemented) \n");
	printf("  -s <num>\t Number of set index bits \n");
	printf("  -E <num>\t Number of lines per set \n");
	printf("  -b <num>\t Number of block offset bits \n");
	printf("  -t <file>\t Trace of file \n");
	return;
}


/*
 simulates cache for some target file
 returns 1 for user asking for information
 returns 0 on completion
 returns -1 on input error
 can crash when the user doesn't supply a proper valgrind trace
*/
int main(int argc, char **argv){

	switch(initializeGlobals(argc, argv)){
		case 1:
			usageMessage(argv);
			return 1;
			
		case -1:
			usageMessage(argv);
			return -1;
			
		case 0:
			break;
	}
	if(checkArguments()){
		printf("Invalid/incorrect arguments supplied \n");
		usageMessage(argv);
		return -1;
	}

	initializeCache();
	runFileLines();
	printSummary(_hits, _misses, _evictions);
	return 0;
}
