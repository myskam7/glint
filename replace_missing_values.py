from numpy import loadtxt, savetxt, where, zeros, delete, mean
import argparse

def _replace_missing_values_in_matrix(all_data, missing_value_indicator, data_max_missing_values, samples_max_missing_values, replace = False, data_type = float):
    number_of_data, number_of_samples = all_data.shape
    na_count_per_sample  = zeros(number_of_samples)

    data_indices_to_remove = []
    print "Replacing missing values by mean..."
    for i, data_for_all_samples in enumerate(all_data):
        na_indices = where(data_for_all_samples == missing_value_indicator)[0]
        na_count_per_sample[na_indices] += 1 
        na_count = len(na_indices)
        na_percentage = float(na_count) / number_of_samples
        if na_percentage > data_max_missing_values:
            data_indices_to_remove.append(i)
        else:
            if na_count != 0 :
                # "predict" using mean of non-missing samples in this snp
                non_na_indices = delete(range(number_of_samples), na_indices)
                if replace:
                    all_data[i][na_indices] = mean(data_for_all_samples[non_na_indices].astype(data_type))
                else:
                    all_data[i][na_indices] = mean(data_for_all_samples[non_na_indices])

    samples_indices_to_keep = where(na_count_per_sample < number_of_samples * samples_max_missing_values)[0]
    print "Removed %s samples with more than %s missing values" % (number_of_samples - len(samples_indices_to_keep), samples_max_missing_values)
    data_indices_to_keep = delete(range(number_of_data), data_indices_to_remove)
    print "Removed %s data with more than %s missing values" % (len(data_indices_to_remove), data_max_missing_values)

    return all_data[data_indices_to_keep,:][:,samples_indices_to_keep]

def get_data_type(data_type_str):
    if data_type_str == 'float' or data_type_str == 'double':
        return float
    if data_type_str == 'int' or data_type_str == 'integer':
        return int
    return None

def replace_missing(data_filename, missing_value_indicator, data_max_missing_values, samples_max_missing_values, data_type = float, sep = " ", suffix = ".non_missing_values", dim=2):
    """
    replaces missing values by mean of non-missing data/samples and saves the output to the file named data_filename + suffix
    if there are too many missing samples (more than samples_max_missing_values) - they are removed
    if there are too mant missing datas (more than data_max_missing_values) - they are removed

    parames:
    data_filename - a matrix of type int or float. dimensions nXm where n is number of samples and m number of data(e.g sites)
    assumes data_filename format is

            sample_0, .., sample_n
    data_0
    .
    .
    data_m

    transpose before sending to function if you have different format

    missing_value_indicator - the missing value char (int, float or string) in your data 
    data_max_missing_values - the maximum data missing values allowed  (percantage - values between 0 and 1)
    samples_max_missing_values - the maximum sample missing values allowed  (percantage - values between 0 and 1)
    data_type - the daya type in the matrix found in data_filename - must be  float or int
    sep - the separator sign of the matrix in data_filename
    suffix - the suffix for the output filename


    returns array of non-missing data/samples
    """
    #convert data_type from string to type ('float' --> float)
    original_data_type = data_type
    data_type = get_data_type(data_type)

    if data_type == None:
        raw_input("Error: data type must be float or int, not %s" % original_data_type)
        return None
    
    #find the right missing value indicator type 
    replace = False
    float_ind = None
    int_ind = None
    try:
        # a string representing an int can be converted to both float and int
        # but a string representing a float cant be converted to int
        # that's why we check the float conversion first
        float_ind = float(missing_value_indicator) 
        int_ind = int(missing_value_indicator)
    except:
        pass
    # if both int_ind and float_int are not None - the string represent an int.
    # (if it represent an float -  it cant be converted to int) so its enough to check the int alone

    # if indicator type is not str - we'll use the original datatyp
    # if it is str - ew'll read the data as strings, find the indicator and convert it back to datatype
    if int_ind is not None: 
        missing_value_indicator = int_ind
    elif float_ind is not None:
        missing_value_indicator = float_ind
    else:
        data_type = str
        replace = True

    try:
        all_data = loadtxt(data_filename, dtype=data_type, delimiter=sep)
        if all_data.ndim != dim:
            raw_input("Error: got data from dimensions %d while excepted to %d. Please check all paramenters are OK (data type and separator)." %(all_data.ndim, dim))
            return None
        output_filename = data_filename + suffix

        if replace:
            data_type = original_data_type

        output_data = _replace_missing_values_in_matrix(all_data, missing_value_indicator, data_max_missing_values, samples_max_missing_values, replace, data_type)
        print "Output is saved to " + output_filename
        savetxt(output_filename, output_data, fmt='%s')
        return output_data

    except Exception as e:
        raw_input("Error loading data file. please check that data_type, separator and missing value indicator Ok\n%s"%e)
    

def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    

    parser.add_argument("--datafile", required=True, type=str, help="the matrix data filename")
    parser.add_argument("--ind", type=str, required=True, help="the missing value char (or any sign) in your data" )
    parser.add_argument("--max_d",required=True, type = float, help="the maximum data missing values allowed  (percantage - values between 0 and 1)")
    parser.add_argument("--max_s", required=True,type = float, help="the maximum sample missing values allowed  (percantage - values between 0 and 1)")
    parser.add_argument("--dtype", type=str, default='float', help="the daya type in the matrix found in data_filename. must be float or int Default is float")
    parser.add_argument("--sep", type=str, default=" ", help="the separator sign of the matrix in data_filename. Default is single whitespace. please write \"\t\" for tab")
    parser.add_argument("--suffix", type=str, default=".non_missing_values", help="the suffix for the output filename")
    parser.add_argument("--dim", type=int, default=2, help="the dimensions of the matrix in the datafile. Default is 2")
    

    return parser.parse_args(args=argv)

args = parse_args()
replace_missing(args.datafile, args.ind, args.max_d, args.max_s, args.dtype, args.sep , args.suffix, args.dim)
