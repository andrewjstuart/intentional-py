import argparse

program_name: str = "intentional"
version_number: str = "0.1.0"

# initialize Parser
parser = argparse.ArgumentParser(
    prog=program_name,
    description="This is a script to create Dialogflow ES Intents",
    epilog="See the README for more information",
)
nl = parser.add_argument_group("Natural Language Mode")
nl.add_argument(
    "-nl",
    "--natural-language",
    action="store_true",
    help="Use the script in NL mode using specific NL config and directories for training phrases.",
)
nl.add_argument(
    "-r",
    "--reuse",
    action="store_true",
    help="Reuse the previously created NL config file.",
)
nl.add_argument(
    "-v",
    "--vertical",
    action="store",
    help="Vertical prefix abbreviation used for the NL intent names. **This will rebuild NL config file**",
    type=str,
    nargs="?",
)
nl.add_argument(
    "-c",
    "--context",
    action="store",
    help="Context used for the NL intent names (default: %(default)s). **This will rebuild NL config file**",
    type=str,
    nargs="?",
    default="GetIntent",
)
nl.add_argument(
    "-lc",
    "--lowercase",
    action="store_true",
    help="Certain clients coded the NL actions in lowercase instead of the standard uppercase. This should only be used for these clients that already have been using it.",
)
parser.add_argument(
    "--config",
    action="store",
    help="Name of the config file when not using the standard files.",
    type=str,
    nargs="?",
    default="intents.cfg",
)
parser.add_argument(
    "-q", "--quiet", action="store_true", help="Use this flag to suppress output."
)
# parser.add_argument(
#    "-validate",
#    "--validate",
#    action="store_true",
#    help="Check for existing files. If using NL then also check for duplicates phrases in the data. This will not create the intents, but will do all the validations.",
# )
parser.add_argument("--version", action="version", version=f"%(prog)s {version_number}")
# Read arguments from the command line
args = parser.parse_args()

print(args)

# if args.Output:
#    print("Output is: ", args.Output)
