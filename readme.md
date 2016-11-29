# IBM XCLI python client

This repository contains a Python client for executing XIV CLI commands.
This protocol is relevant for IBM XIV, Spectrum Accelerate, FlashSystem A9000
and FlashSystem A9000R storages.
The client enables full management and monitoring of the storage arrays.

## Getting Started

Clone the repository, add it to your PYTHONPATH. The XCLI client is ready for import and use.

## Usage examples

Usage examples of the client are available in examples.py

## XCLI command example

Each storage system maintains its own CLI command set. The commands are detailed in the XCLI Reference Guides available on IBM Knowledge Center (KC).

To display an XCLI Reference Guide:

1. Navigate to a storage system welcome page on KC:

IBM FlashSystem A9000: http://www.ibm.com/support/knowledgecenter/STJKMM/landing/IBM_FlashSystem_A9000_welcome_page.html

IBM FlashSystem A9000R: http://www.ibm.com/support/knowledgecenter/STJKN5/landing/IBM_FlashSystem_A9000R_welcome_page.html

IBM XIV-Gen3: http://www.ibm.com/support/knowledgecenter/STJTAG/com.ibm.help.xivgen3.doc/xiv_gen3kcwelcomepage.html

IBM Spectrum Accelerate: http://www.ibm.com/support/knowledgecenter/STZSWD/landing/IBM_Spectrum_Accelerate_welcome_page.html

2. On a welcome page, use the drop-down list to select a storage system microcode version. For example, for FlashSystem A9000 you can currently choose "IBM FlashSystem A9000 12.0.x". The welcome page for the specific microcode version is displayed.

3. On the microcode version welcome page, click "PDF publications" to display the Publications and related information page.

4. On the Publications and related information page, click "Download" in the CLI Reference Guide row to display the relevant reference guide in the PDF format.


## Contributing
We do not accept any contributions at the moment.
This may change in the future, so you can fork, clone, and suggest a pull request.

## Running tests
Use nosetests command to run a test.

    nosetests -v
