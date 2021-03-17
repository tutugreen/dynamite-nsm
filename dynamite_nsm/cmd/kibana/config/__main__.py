from dynamite_nsm.cmd.kibana.config import main
from dynamite_nsm.cmd.kibana.config import get_action_parser

if __name__ == '__main__':
    parser = get_action_parser()
    args = parser.parse_args()
    try:
        if args.sub_interface == 'main':
            print(main.interface.execute(args))
    except AttributeError:
        parser.print_help()
