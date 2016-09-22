#!/usr/bin/env python
import validate_dependencies
import argparse
import os
import sys
from configuration import configurelogging
import logging
from utils import common
from numpy import loadtxt
from utils import GlintArgumentParser
from parsers import ModuleParser, RefactorParser, EWASParser, \
                    MethylationDataParser, PredictorParser, \
                    EpistructureParser, LMMParser, PlotParser  #dont remove this is imported in,,,

LOGGER = configurelogging.ConfigureLogging()

class GlintParser(ModuleParser):
    def __init__(self, parser):
        """
        --out: a prefix that will be added to any file the program will output.
                If not supplied, default filenames will be used, and will override each other on the next run. 
        --loglevel: the loglevel to use. default is INFO. program terminates if it is not one of the list specified in configurelogging.OPTIONAL_LEVELS
        
        flow:
            First the program validates that all the required flags for all the selected mofules are specified and valid, otherwise it terminates
            with a proper message.
            This is done before data is loaded.

            No datafile need to be provided in the following cases:
                if --predict is selected,
                if --qqplot --manhattan are selected without any --ewas test 

            Otherwise (datafile must be provided):
                 - samples preprocessing is done before executing anything else (remove / keep samples). The new methData will be used in the next modules
                 - refactor is executed if asked (with a new methData copy)
                   Its components are added (always) as covariates to the methylation data (which will be used in the next modules)
                 - sites preprocessing is done (exclude / include sites). The new methData will be used in the next modules 
                 - methData is saved as glint file if asked
                 - run ewas test if asked (with a new methData copy)
                 - run plot if asked (with a new methData copy) (with the results of the ewas test, this is OK because if ewas test wasn't selecten than plot would have been executed first (see above))
                 - run epistructure is asked (with a new methData copy)
                 - 
            * Note that a new copy of methylation data object is created for any module
            * modules that should not run together
                 - refactor and lmm (refactor will be executed twice as documented in LMMParser)
                 - epistructure and refactor
                 - which more? TODO Elior
        """
        optional = parser.add_argument_group('3.Optional arguments')
        optional.add_argument('-h', '--help', action='help', help = "print this help") # add help here so it will be under same group with all other optional argument
        optional.add_argument('--out', type = str,   help = "changes the prefix of the output file ")
        def loglevel_value(val):
            # val = int(val)
            if val.lower() not in configurelogging.OPTIONAL_LEVELS.keys():
                common.terminate("log level is not valid. should be one of %s" % str( configurelogging.OPTIONAL_LEVELS.keys()))
            return configurelogging.OPTIONAL_LEVELS[val]
        optional.add_argument('--loglevel', type = loglevel_value,  default = 'info', help = "the log level to print")

        modules = parser.add_argument_group('4.Glint modules')
        modules.add_argument('--refactor', action='store_true', help = "<TODO Elior, add help here>")
        modules.add_argument('--ewas',     action='store_true', help = "<TODO Elior, add help here>" )
        modules.add_argument('--predict',  action='store_true', help = "<TODO Elior, add help here methylation predictor>" )
        modules.add_argument('--epi',      action='store_true', help = "<TODO Elior, edit>" )
        modules.add_argument('--plot',     action='store_true', help = "<TODO Elior, edit>" )

        super(GlintParser, self).__init__(optional, modules)
    

class ModulesArgumentParsers(object):
    FUNCTIONALITY_ARGS = ['--plot', '--refactor', '--ewas', '--predict'] # TODO find better way to hold arguments that cause some functionality. glint is not supposed to be aware of those args
    DATA_FUNC_ARGS = ['--gsave'] 
    DATA_PREPROCESSING_NOT_RELEVANT_FOR_REFACTOR = ['--include', '--exclude', '--minmean', '--maxmean']
    SOLE_ARGS = ['--epi'] # functilnality flags that cannot be specified with other functionaity flags

    def __init__(self, user_args_selection):
        self.selected_args = user_args_selection
        self.parser = GlintArgumentParser(prog=os.path.basename(sys.argv[0]),
                             description = "<<todo add help before >>",
                             epilog = "<< todo add help after >>",
                             add_help=False) # don't add help because it is added in 'optional group'

        self.glint_parser = None
        self.meth_parser = None
        self.refactor_parser = None
        self.ewas_parser = None
        self.epi_parser = None
        self.plot_parser = None
        self.args = None

    def add_arguments(self):
        # Notice to add arguments by the order you want them to be printed in --help

        #main
        self.meth_parser = MethylationDataParser(self.parser)
        self.glint_parser = GlintParser(self.parser)

        #modules in the order they'll appear on --help
        self.refactor_parser = RefactorParser(self.parser)
        self.ewas_parser = EWASParser(self.parser)
        self.predictor_parser = PredictorParser(self.parser)
        self.epi_parser = EpistructureParser(self.parser)
        self.plot_parser = PlotParser(self.parser)

    def parse_args(self):
        logging.info("Validating arguments...")
        self.args = self.parser.parse_args()

        optional_args = []
        self.glint_parser.validate_args(self.args)
        optional_args.extend(self.glint_parser.all_args)


        # prediction runs without datafile
        if self.args.predict:
            self.predictor_parser.validate_args(self.args)
            optional_args.extend(self.predictor_parser.all_args)

            self.check_selected_args(optional_args)
            return self.args

        #plot runs without datafile but could receive datafile if run with ewas
        if self.args.plot:
            self.plot_parser.validate_args(self.args)
            optional_args.extend(self.plot_parser.all_args)
            if not self.args.ewas:
                self.check_selected_args(optional_args)
                return self.args

    

        self.meth_parser.validate_args(self.args)
        optional_args.extend(self.meth_parser.all_args)    

        self.epi_parser.validate_args(self.args)
        optional_args.extend(self.epi_parser.all_args)
        
        if self.args.refactor:
            self.refactor_parser.validate_args(self.args)
            optional_args.extend(self.refactor_parser.all_args)
        # ewas tests need to be after refactor
        if self.args.ewas:
            self.ewas_parser.validate_args(self.args)
            optional_args.extend(self.ewas_parser.all_args)

        self.check_selected_args(optional_args)
        return self.args


    def check_selected_args(self, optional_args):
        """
        validates that the user selected "action" argument (and didn't supply just a datafile) 
        and that the user didnt select an argument that is not an option for him (argument from a module that wasn't selected)
        """
        selected_args = set(self.selected_args)
        data_func_args = set(self.DATA_FUNC_ARGS)
        func_args = set(self.FUNCTIONALITY_ARGS)
        all_func_args = set(self.FUNCTIONALITY_ARGS + self.DATA_FUNC_ARGS)
        optional_args = set(optional_args)
        sole_args = set(self.SOLE_ARGS)
        args_not_relevant_for_refactor = set(self.DATA_PREPROCESSING_NOT_RELEVANT_FOR_REFACTOR)
        all_func_args.update(sole_args)

        func_args_chosen = selected_args.intersection(all_func_args)
        args_not_relevant_for_refactor_chosen = selected_args.intersection(args_not_relevant_for_refactor)
        sole_args_chosen = selected_args.intersection(sole_args)

        if len(func_args_chosen) == 0:
            common.terminate("Nothing to do with the data, select at least one argument from %s" % ", ".join(list(all_func_args)))

        elif ((len(func_args_chosen) > (len(sole_args_chosen) + len(data_func_args))) and (len(sole_args_chosen) > 0))or (len(sole_args_chosen) > 1):
            common.terminate("options from %s cannot be specified with any other flags in the same command. you chose %s" % (str(list(sole_args)), str(list(func_args_chosen))))

        differ = selected_args.difference(optional_args)
        if differ:
            common.terminate("selected redundent argument" + str(list(differ)))

        # warn if only refactor module is selected and  user selectes data management flags that are not relevant for refactor
        if self.args.refactor and len(func_args_chosen) == 1:
            not_relevant_atgs = list(args_not_relevant_for_refactor_chosen)
            if len(not_relevant_atgs) != 0:
                logging.warning("selected data management arguments which are not relevant for refactor: %s" % str(not_relevant_atgs))

    def run(self):
        if self.args.predict:
            self.predictor_parser.run(args)
            return

        if (self.args.qqplot or args.manhattan) and not self.args.ewas: # if user asked to run plot without running EWAS test, run plot and quit
            self.plot_parser.run(args)
            return

        self.meth_parser.run(self.args)
        self.meth_parser.preprocess_samples_data() # preprocess samples before refactor and before ewas
        self.meth_parser.preprocess_sites_data() #preprocess sites before refactor and before ewas
        
        if self.args.refactor:
            refactor_meth_data = self.meth_parser.module.copy()
            self.refactor_parser.run(args = self.args,
                                    meth_data = refactor_meth_data,
                                    output_perfix = self.args.out)
            logging.info("adding refactor components to covariates, set --gsave to save new methData")
            self.meth_parser.module.add_covar_datas(self.refactor_parser.module.components, "rc") # add refactor components as covariate file

        
        # ewas tests must be called after refactor
        ewas_results = None
        if self.args.ewas:
            ewas_meth_data = self.meth_parser.module.copy()
            ewas_results = self.ewas_parser.run(args = self.args,
                                               meth_data = ewas_meth_data)

        if self.args.plot: # if not selected should we plot by default?
            plot_meth_data = self.meth_parser.module.copy()
            self.plot_parser.run(args, meth_data = plot_meth_data, ewas_result_obj = ewas_results)



        if self.args.epi:
            epi_met_data = self.meth_parser.module.copy()
            self.epi_parser.run(args = self.args,
                                meth_data = epi_met_data,
                                output_perfix = self.args.out)
            self.meth_parser.module.add_covar_datas(self.epi_parser.module.components, "epi") # add refactor components as covariate file


        self.meth_parser.gsave(output_perfix = self.args.out) #save after all preprocessing  add epi and refactor covars 
        

if __name__ == '__main__':
    selected_args = [arg for arg in sys.argv if arg.startswith("--")] 
    parser = ModulesArgumentParsers(selected_args)

    parser.add_arguments()
    args = parser.parse_args()
    LOGGER.setLoggerLevel(args.loglevel)

    logging.info("Starting glint...")
    parser.run()




