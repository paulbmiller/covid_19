import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# CONSTANTS
MAX_CANTONS = 8


def import_csv_total(filepath):
    return pd.read_csv(filepath)


def check_inconsistencies(df, cantons, columns, fillna=False, verbose=False):
    """
    This function will go through the given columns and check for
    inconsistencies in the values for each canton by looking at previously
    seen values. Mainly, it checks that cumulative values do not go down. It
    also assumes that no values means no change from the previous one and that
    no reported values ever means 0.
    
    It can also be used to fill NaN values in the DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        Main DataFrame object.
    cantons : array-like
        List of canton abbreviations.
    columns : array-like
        List of column names.
    fillna : bool
        Fill NaN values.
    verbose : bool
        Print an output for every inconsistency found.

    Raises
    ------
    Exception
        In the case that the column is not cumulative.

    Returns
    -------
    inconsistencies : list
        List of tuples of inconsistencies found (list of (index, column)).

    """
    inconsistencies = []
    for col_name in columns:
        for canton in cantons:
            has_value = False
            max_value = 0.
            for index in df.loc[df.canton == canton, col_name].index:
                if not has_value:
                    if np.isnan(df.loc[index, col_name]) and fillna:
                        df.loc[index, col_name] = max_value
                    else:
                        has_value = True
                        max_value = df.loc[index, col_name]
                else:
                    if np.isnan(df.loc[index, col_name]) and fillna:
                        df.loc[index, col_name] = max_value
                    elif max_value > df.loc[index, col_name]:
                        inconsistencies.append((index, col_name))
                        if verbose:
                            print('Cumulative number smaller than the previous one. Wrong value for column {} at index {}'.format(col_name, index))
                    else:
                        max_value = df.loc[index, col_name]

    print('{} Inconsistencies found in cumulative numbers.'.format(
        len(inconsistencies)))
    return inconsistencies


def no_same_day_reports(df):
    inc = []
    for canton_name in df.canton.unique():
        if not df.loc[df.canton == canton_name, 'date'].is_unique:
            inc.append(canton_name)

    if len(inc) > 0:
        print("{} cantons have same day reports.".format(len(inc)))
    else:
        print("No cantons have same day reports.")

    return inc


def make_new_df(df, cumul_columns):
    # Create a full dataframe of all cumulative columns
    # Assumes no reports means no change
    min_date = df.date.min()
    max_date = df.date.max()
    cols = ['date', 'canton']
    cols.extend(cumul_columns)
    date_range = pd.date_range(min_date, max_date)
    
    full_df = pd.DataFrame(
        index=range(len(date_range) * len(df.canton.unique())),
        columns=cols)

    list_of_dates = []
    for i in date_range:
        list_of_dates.extend([str(i)[0:10]] * len(df.canton.unique()))
    
    full_df.date = pd.Series(list_of_dates)

    canton_series = pd.Series(df.canton.unique())
    full_df.canton = pd.concat([canton_series] * len(date_range),
                               ignore_index=True)

    for index in df.index:
        row = df.loc[index]
        canton = row.canton
        date = row.date
        full_df_id = full_df[
            full_df.canton == canton].loc[full_df.date == date].index[0]

        for col in cumul_columns:
            if not np.isnan(row[col]):
                full_df.loc[full_df_id, col] = row[col].astype(float)

    return full_df


def draw_plot(df, column, cantons=None, exclude_FL=True, remove_cumul=False):
    if cantons is None:
        cantons = df.canton.unique()

        if exclude_FL:
            plt_title = 'Sum of {} in Switzerland'.format(column)
            plt.locator_params(axis='x', nbins=5)
            df_sums = df[df.canton != 'FL'].groupby(['date'])[column].sum()
            if remove_cumul:
                df_sums[1:] = df_sums[1:] - df_sums[:-1].to_numpy()
                df_sums[df_sums < 0] = 0
            df_sums.plot(title=plt_title)
        else:
            plt_title = 'Sum of {} in Switzerland and FL'.format(column)
            plt.locator_params(axis='x', nbins=5)
            df_sums = df.groupby(['date'])[column].sum()
            if remove_cumul:
                df_sums[1:] = df_sums[1:] - df_sums[:-1].to_numpy()
                df_sums[df_sums < 0] = 0
            df_sums.plot(title=plt_title)

    else:
        plt.figure()
        plt.locator_params(axis='x', nbins=5)
        top_cantons = df[df.date == df.date.max()].loc[
            :, ['canton', column]].nlargest(50, column).canton.to_numpy()

        if len(cantons) > 1:
            if len(cantons) < MAX_CANTONS:
                plt_title = 'Sum of {} for cantons {}'.format(
                    column, '/'.join(cantons))
                plt.legend(cantons, loc='upper left')
            else:
                plt_title = 'Sum of {} for cantons'.format(column)

            for canton in top_cantons:
                df_sums = df[df.canton == canton].groupby(
                    ['date'])[column].sum()
                if remove_cumul:
                    df_sums[1:] = df_sums[1:] - df_sums[:-1].to_numpy()
                    df_sums[df_sums < 0] = 0
                df_sums.plot(title=plt_title)
                plt.legend(top_cantons[0:MAX_CANTONS], loc='upper left')

        else:
            plt_title = 'Sum of {} for canton {}'.format(column, cantons[0])
            df_sums = df[df.canton == cantons[0]].groupby(
                ['date'])[column].sum()
            if remove_cumul:
                df_sums[1:] = df_sums[1:] - df_sums[:-1].to_numpy()
                df_sums[df_sums < 0] = 0
            df_sums.plot(title=plt_title)
            plt.legend(loc='upper left')


if __name__ == '__main__':
    df = import_csv_total('COVID19_Fallzahlen_CH_total.csv')
    df = df.drop(columns='source')
    df = df.rename(columns={'abbreviation_canton_and_fl': 'canton'})
    cumul_columns = ['ncumul_tested', 'ncumul_conf', 'ncumul_hosp',
                     'ncumul_ICU', 'ncumul_vent', 'ncumul_released',
                     'ncumul_deceased']

    errors = check_inconsistencies(df, df.canton.unique(), cumul_columns,
                                   fillna=False)
    canton_reports = no_same_day_reports(df)

    # Drop the time column since there normally aren't any same day reports
    df = df.drop(columns='time')

    full_df = make_new_df(df, cumul_columns)

    errors = check_inconsistencies(full_df, full_df.canton.unique(),
                                   cumul_columns, fillna=True)

    for col in cumul_columns:
        full_df[col] = full_df[col].astype(int)

    # draw_plot(full_df, 'ncumul_deceased', ['FR'], exclude_FL=False,
    #           remove_cumul=True)
    # draw_plot(full_df, 'ncumul_deceased', full_df.canton.unique(),
    #           remove_cumul=False)
    # Example of graphing deaths in canton FR
    # df[df.canton == 'SG'].plot(x='date', y='ncumul_deceased')
