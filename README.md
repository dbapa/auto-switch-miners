# auto-switch-miners for Linux

I noticed there wasn't an easy way to use a auto miner switching like that done by NiceHash on Windows. Most of the utilities are available only for Windows. So created this script that can be used to switch miners on Linux.

For Linux (and should work with windows, though not tested)

This program is intended to be used as an auto switching utility to decide and chose the right miner based on 24h profitability report as suggested by whattomine.

By allowing users to specify and configure the coin-algorithm pair, or algorithms to be matched to your own custom scripts, it provides flexibility in choosing any specific miner you desire for a specific coin-algorithm pair.

All the configurations for this program utility are done in the input.cfg file -

Section A] 
To customize and mimic input parameters to what you typically input on the whattomine.com page.

Section B] 
To specify the choice of miners to be used based on 'coin-algorithm'=start_miner_script or 'algorithm'=start_miner_script format.
start_miner_script should typically point to a miner initialization script. E.g. I have a sub directory for ethminer and have the miner trigger script file named 'nicehash.sh'. So my entry would be "Nicehash-ethash=ethminer/nicehash.sh"


Dependencies & Prerequisites:
1) python 3.5 or above (if you are mining on Ubuntu 16.04 or above, you likely have python3 pre-installed)
2) .sh files to start desired miners (this program is a miner switching utility that uses your existing miners that are configured to be started using customized .sh scripts)


Usage:

Step 1) Download the auto-pilot.py, input.cfg and start-auto-pilot.sh to your local folders. The specifis miners that you have specified in the input.cfg file have a relative path to this folder. So these program files should be located in the same folder (base folder) where you have all your miners.
e.g. the sample input.cfg file assumes there are 3 folders: zm_0.6.1, ethminer and bminer, respectively in the base directory where the auto-pilot.py file is located. The path for the sh files is specified relative to the current directory

Step 2) Update the input.cfg file for your setup and miners. 

Step 3) Use following commands:
$chmod +x start-auto-pilot.sh
$./start-auto-pilot.sh




License:
You are free to use this script for your personal rigs/custom gaming pc based miners. 

Encourage donations to following address:

BTC: 3HoBJWxN9HWGmNU4FTfAthqnj1j52Y9ZyX 

ETH: 0xBb8DaaaFA18B01DF169e197988Ed708e868508D5 

LTC: MXC6KNMr75mruK3Bsv62hMaJ9UBeEaNXn8
