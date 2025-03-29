# pPIM ISA Converter Setup Guide

## Team Members

- **Prem Sundaresan** (22BAI1325)
- **Gorav Jhabakh** (22BAI1037)
- **Vamsee N Yashwanth** (22BAI1313)

## Prerequisites

### Install Clang + LLVM

1. Download Clang + LLVM from the official repository:\
   [LLVM 18.1.8 Release](https://github.com/llvm/llvm-project/releases/tag/llvmorg-18.1.8)
2. Download the **tar file** and extract it.
3. Add the extracted **bin folder path** to the **PATH** environment variable in system settings.

### Install Streamlit (for Frontend)

Run the following command to install Streamlit:

```sh
pip install streamlit
```

## Running the Application

To launch the Streamlit frontend, use:

```sh
streamlit run file_path
```

*Replace **`file_path`** with the actual path to **`main.py`**.*

### Quick Start

The easiest way to run the app:

1. Open a terminal in the project directory.
2. Run:
   ```sh
   streamlit run main.py
   ```