WHAT the app will look like.

 1. Visit the page and authenticate using openid.

 2. You see two CodeMirror2 boxes with something like this in them:

    Status: Running sage process started 19 minutes ago.

    [                                   ]
    [                                   ]
    [ sage: a = 5                       ]          (read only box, with scroll bars)
    [ sage: b = 7                       ]
    [ sage: factor(a^2 + b^3)           ]	   
    [ 2^4 * 23                          ]


    [ for i in range(3):                ]          (you type this)
    [    print a*(b+i)                  ]          (write-able box) 
    evaluate
 

 3. Type 1 or more lines of code into the second box and click
    evaluate (or press shift-enter).
 
 4. In a fraction of a second the above two boxes change to look like this:

    Status: Running sage process started 20 minutes ago.

    [                                   ]
    [ sage: a = 5                       ]          (read only box)
    [ sage: b = 7                       ]
    [ sage: factor(a^2 + b^3)           ]	   
    [ 2^4 * 23                          ]
    [ sage: for i in range(3):          ]
    [ ...       print a*(b*i)           ]
    [*                                  ]

    [                                   ]
    [                                   ]          (write-able box) 
    evaluate

 5. In a fraction of a second more they look like this:

    Status: Running sage process started 20 minutes ago.

    [                                   ]
    [ sage: a = 5                       ]          (read only box, with scroll bars)
    [ sage: b = 7                       ]
    [ sage: factor(a^2 + b^3)           ]	   
    [ 2^4 * 23                          ]
    [ sage: for i in range(3):          ]
    [ ...       print a*(b*i)           ]
    [ 35                                ]
    [ 40                                ]
    [ 45                                ]

    [                                   ]
    [                                   ]          (write-able box) 
    evaluate


Behind the scenes there is <= 1 persistent session for each user. 


---------------------------------


