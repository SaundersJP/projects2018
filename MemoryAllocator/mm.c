#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <unistd.h>
#include <string.h>

#include "mm.h"
#include "memlib.h"

/*********************************************************
 * NOTE TO STUDENTS: Before you do anything else, please
 * provide your team information in the following struct.
 ********************************************************/
team_t team = {
    /* Team name */
    "Last Minute Executor",
    /* First member's full name */
    "Jonathan Saunders",
    /* First member's WUSTL key */
    "458332",
    /* Second member's full name (leave blank) */
    "",
    /* Second member's WUSTL key (leave blank) */
    ""
};

static void * heap_listp;

/* single word (4) or double word (8) alignment */
#define WSIZE 4
#define ALIGNMENT 8 
#define LSIZE 4

/* rounds up to the nearest multiple of ALIGNMENT */
#define ALIGN(size) (((size) + (ALIGNMENT - 1)) & ~0x7)


#define SIZE_T_SIZE (ALIGN(sizeof(size_t)))

#define CHUNKSIZE (1<<12)

#define MAX(x, y) ((x) > (y) ? (x) : (y))

#define PACK(size, alloc) ((size) | (alloc))

#define GET(p) (*(unsigned int *) (p))
#define PUT(p, val) (*(unsigned int *) (p) = (val) )

#define GET_SIZE(p) (GET(p) & ~0x7)
#define GET_ALLOC(p) (GET(p) & 0x1)

#define HDRP(bp) ((char *)(bp) - 3*WSIZE)
#define FTRP(bp) ((char *)(bp) + GET_SIZE(HDRP(bp)) - 4*WSIZE)

#define NXTP(bp) ((char *) ((bp) - 2*WSIZE) )
#define PRVP(bp) ((char *) ((bp) - WSIZE) )

#define NEXT_BLKP(bp) ((char *)(bp) + GET_SIZE(HDRP(bp)))
#define PREV_BLKP(bp) ((char *) ((bp) - GET_SIZE(HDRP(bp) - WSIZE)) )//((char *)(bp) - WSIZE)



 
 //////////////////////////////////////////////////
 //////////////////////////////////////////////////
 //////////////////////////////////////////////////
 
 static void excise(void *ptr){
	char *nextBlock = (char *) GET(NXTP(ptr));
	char *prevBlock = (char *) GET(PRVP(ptr));
	

	if(nextBlock && prevBlock){
		PUT(PRVP(nextBlock), prevBlock);
		PUT(NXTP(prevBlock), nextBlock);
	}
	return;
 }
 
 static void putAtFront(void *bp){
	 char * nextBlock = (char *) GET(NXTP(heap_listp));
	 
	 PUT(NXTP(bp), nextBlock);
	 PUT(PRVP(nextBlock), bp);
	 
	 //set prefix node as our head and set our bp as prefix->next
	 PUT(PRVP(bp), heap_listp);
	 PUT(NXTP(heap_listp), bp);
	 return;
 }
 
 static void *coalesce(void *bp){
	char *nextBlock = (char *) GET(NXTP(heap_listp));
	
	char * nextAdj = NEXT_BLKP(bp);
	char * prevAdj = PREV_BLKP(bp);
	
	size_t prev_alloc = GET_ALLOC(FTRP(prevAdj));
	size_t next_alloc = GET_ALLOC(HDRP(nextAdj));
	size_t size = GET_SIZE(HDRP(bp));
	
	
	//previous and next are allocated
	if(prev_alloc && next_alloc) {
		return bp;
	}
	
	//next is not allocated
	else if (prev_alloc && !next_alloc) {
		size += GET_SIZE(HDRP(NEXT_BLKP(bp)));
		
		excise(nextAdj);
		
		PUT(HDRP(bp), PACK(size, 0));
		PUT(FTRP(bp), PACK(size, 0));		
		
		
	    putAtFront(bp);
	}
	
	//previous is not allocated
	else if (!prev_alloc && next_alloc) {
		size += GET_SIZE(HDRP(PREV_BLKP(bp)));
		
		excise(prevAdj);
		
		PUT(FTRP(bp), PACK(size, 0));
		PUT(HDRP(PREV_BLKP(bp)), PACK(size,0));
		bp = PREV_BLKP(bp);
		
		putAtFront(bp);
	}
	
	//both are unallocated
	else{
		size += GET_SIZE(HDRP(PREV_BLKP(bp))) + GET_SIZE(FTRP(NEXT_BLKP(bp)));
		
		excise(prevAdj);
		excise(nextAdj);
		
		PUT(HDRP(PREV_BLKP(bp)), PACK(size, 0));
		PUT(FTRP(NEXT_BLKP(bp)), PACK(size, 0));
		bp = PREV_BLKP(bp);
		
		putAtFront(bp);
	}
	
	return bp;
}

 
  static void *extend_heap(size_t words){
	 char *bp;
	 char *nextBlock = (char *) GET(NXTP(heap_listp));
	 size_t size;
	 

	 size = (words % 2) ? (words+1) * WSIZE : words * WSIZE;
	 
	 if ((long)(bp = mem_sbrk(size)) == -1){
		return NULL;
	 }
	 
	 
	 //set header
	 PUT(HDRP(bp), PACK(size, 0));
	 
	 //set next to the first thing in out list and change previous of the old block
	 PUT(NXTP(bp), nextBlock);
	 PUT(PRVP(nextBlock), bp);
	 
	 //set prefix node as our head and set our bp as prefix->next
	 PUT(PRVP(bp), heap_listp);
	 PUT(NXTP(heap_listp), bp);
	 
	 //set footer
	 PUT(FTRP(bp), PACK(size, 0));
	 
	 return coalesce(bp);
 }
 
 static void place(void *bp, size_t asize){
	size_t csize = GET_SIZE(HDRP(bp));
	void *next;
	excise(bp);
	
	if((csize - asize) >= (2*ALIGNMENT)) {
		PUT(HDRP(bp), PACK(asize, 1));
		PUT(FTRP(bp), PACK(asize, 1));
		
		next = NEXT_BLKP(bp);
		
		PUT(HDRP(next), PACK(csize-asize, 0));
		PUT(FTRP(next), PACK(csize-asize, 0));
		putAtFront(next);
	}
	
	else{
		PUT(HDRP(bp), PACK(csize, 1));
		PUT(FTRP(bp), PACK(csize, 1));
	}
	return;
 }
 
 static void * find_fit(size_t asize){
	void * bp;
	
	for(bp = heap_listp; GET_SIZE(HDRP(bp)) > 0; bp = GET(NXTP(bp))){
		if( !GET_ALLOC(HDRP(bp)) && (asize <= GET_SIZE(HDRP(bp)))) {
			return bp;
		}
	}
	return NULL;
}

 //////////////////////////////////////////////////
 //////////////////////////////////////////////////
 //////////////////////////////////////////////////
 
 
int mm_init(void)
{

	void * freebp;
	if((heap_listp = mem_sbrk(8*WSIZE)) == (void *) -1){
		return -1;
	}
	//empty
	PUT(heap_listp, 0);
	//header
	PUT(heap_listp + (1*WSIZE), PACK(2*ALIGNMENT, 1));
	//pointer to end and self
	PUT(heap_listp + (2*WSIZE), heap_listp + 8 * WSIZE);
	PUT(heap_listp + (3*WSIZE), heap_listp);
	//footer
	PUT(heap_listp + (4*WSIZE), PACK(2*ALIGNMENT, 1));
	
	//set end
	PUT(heap_listp + (5*WSIZE), PACK(0, 1));
	
	heap_listp += (4*WSIZE);
	

	if((freebp = extend_heap(CHUNKSIZE/WSIZE)) == NULL){
		return -1;
	}

	
    return 0;
}



/* 
 * mm_malloc - Allocate a block by incrementing the brk pointer.
 *     Always allocate a block whose size is a multiple of the alignment.
 */
void *mm_malloc(size_t size)
{
    size_t asize;
	size_t extendSize;
	char *bp;
	
	if(size == 0){
		return NULL;
	}
	
	if(size <= ALIGNMENT){
		asize = 2*ALIGNMENT;
	}
	else{
		asize = ALIGNMENT * ((size + (ALIGNMENT) + (ALIGNMENT - 1)) / ALIGNMENT);
	}
	
	if((bp = find_fit(asize)) != NULL) {
		place(bp, asize);
		return bp;
	}
	
	extendSize = MAX(asize,CHUNKSIZE);
	if ((bp = extend_heap(extendSize/WSIZE)) == NULL){
		return NULL;
	}

	place(bp, asize);
	return bp;
}






/*
 * mm_free - Freeing a block does nothing.
 */
void mm_free(void *bp){
	
	char *nextBlock = NEXT_BLKP(heap_listp);
	size_t size = GET_SIZE(HDRP(bp));
	
	PUT(HDRP(bp), PACK(size, 0));
	
	//set next to the first thing in out list and change previous of the old block
	PUT(NXTP(bp), nextBlock);
	PUT(PRVP(nextBlock), bp);
	
	//set prefix node as our head and set our bp as prefix->next
	PUT(PRVP(bp), heap_listp);
	PUT(NXTP(heap_listp), bp);
	
	PUT(FTRP(bp), PACK(size, 0));
	coalesce(bp);
}


/*
 * mm_realloc - Implemented simply in terms of mm_malloc and mm_free
 */
void *mm_realloc(void *ptr, size_t size)
{
    void *oldptr = ptr;
    void *newptr;
    size_t copySize;
    
    newptr = mm_malloc(size);
    if (newptr == NULL)
      return NULL;
    copySize = *(size_t *)((char *)oldptr - SIZE_T_SIZE);
    if (size < copySize)
      copySize = size;
    memcpy(newptr, oldptr, copySize);
    mm_free(oldptr);
    return newptr;
}














