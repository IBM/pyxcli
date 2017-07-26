# IBM XCLI Python client

This repository contains the IBM Extended Command-line Interface (XCLI) Python client, which establishes terminal connection with IBM XIV, Spectrum Accelerate, FlashSystem A9000, and FlashSystem A9000R storage systems. The Python client protocol enables full management and monitoring of these storage arrays by issuing dedicated command-line interface (CLI) commands.

## Getting started

Clone the repository, and then add it to your PYTHONPATH directory. The Python client is then ready for import and use.

## Usage examples

Usage examples of the Python client are available in the **examples.py** file.

## Displaying the command-line reference information

Each storage system and major software version has its own set of CLI commands. The commands are detailed in the CLI reference guides that are available on IBM Knowledge Center (KC).

To display the full CLI Reference Guide of a specific storage system and a specific software version:

1. Navigate to a storage system welcome page on KC:

IBM FlashSystem A9000: http://www.ibm.com/support/knowledgecenter/STJKMM

IBM FlashSystem A9000R: http://www.ibm.com/support/knowledgecenter/STJKN5

IBM XIV-Gen3: http://www.ibm.com/support/knowledgecenter/STJTAG

IBM Spectrum Accelerate: http://www.ibm.com/support/knowledgecenter/STZSWD

2. On the welcome page, use the drop-down list to select a storage system software version. For example, select **Version 12.1.x**.

![Software version](https://github.com/IBM/pyxcli/blob/master/imgs/1.jpg)

The welcome page of the selected software version is displayed.

3. On the left side of the page, click the **Table of contents** toggle button.

![Table of contents](https://github.com/IBM/pyxcli/blob/master/imgs/2.jpg)

The table of contents for the selected software version is displayed.

4. On the table of contents, click **Reference > Command-line reference**.

![CLI reference](https://github.com/IBM/pyxcli/blob/master/imgs/3.jpg)

5. Refer to **Host and cluster management commands** and to all subsequent chapters.

**Note**:
* The first chapter, **Overview of the command-line interface (CLI)** focuses on how to install and use the Windows-based client utility for issuing CLI commands.  You can skip this chapter if you do not intend to install and use the Windows-based client utility.
* For the PDF version of the CLI Reference Guide, click **Publications** on the table of contents.

## Contributing
We do not accept any contributions at the moment.
This may change in the future, so you can fork, clone, and suggest a pull request.

## Running tests
Use nosetests command to run a test.

    nosetests -v
