Author: orakili (slyseal.orakili@gmail.com)
URLs: http://orakili.org, http://code.google.com/p/slyseal
Thanks to HaxeVideo, Rubyizumi, LibRtmp and some others...

*****Usage*****

How to use Slyseal

**Prerequisites**

All you need is Python 2.6 with the following module: M2Crypto.

It works on both Linux and Windows. It should also work on Mac OSX (not tested).

**Installation**

Simply put the python files where you want.

**Basic Usage**

The default directory to put your videos is the slyseal one or a subdirectory in it.

Start the server by typing "python slyseal.py start".

(On Windows, you'll have to type "slyseal.py -n")

Then you can use your favorite flash video player (see its doc for how to use it with a rtmp server).

A simple demo is available on http://www.orakili.org

**Options**

basic usage: slysleal.py start|stop|restart

-h, --help help

-d, --directory="path/to/files" directory containing the video files (defaults to current directory)

-a, --address=xxx.xxx.xxx.xxx host address (defaults to current host address)

-p, --port=xxxx port (defaults to 1935)

-n, --nodaemon do not start in daemon mode, stay in console mode (only working mode on Windows) 

