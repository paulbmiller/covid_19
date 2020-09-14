import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import lines
import matplotlib


# CONSTANTS
MAX_CANTONS = 8


def preprocess(df_path):
    df = pd.read_csv(df_path)
    
    df = df.drop(columns='source')
    df = df.rename(columns={'abbreviation_canton_and_fl': 'canton'})
    
    """
    Here I define the supposedly cumulative columns. In practice, I do not
    use the ncumul_conf, ncumul_hosp, ncumul_ICU columns because they are
    inconsistent.
    
    cumul_columns = ['ncumul_tested', 'ncumul_conf', 'ncumul_hosp',
                     'ncumul_ICU', 'ncumul_vent', 'ncumul_released',
                     'ncumul_deceased']
    """

    cumul_columns = ['ncumul_tested', 'ncumul_conf', 'ncumul_released',
                     'ncumul_deceased']
    
    # Check that the columns are cumulative numbers
    errors = check_inconsistencies(df, cumul_columns, fillna=True)
    
    canton_reports = no_same_day_reports(df)

    # Drop the time column since there normally aren't any same day reports
    df = df.drop(columns='time')
    
    sorted_df = df.sort_values(by=['canton', 'date'], ignore_index=True)

    full_df = make_new_df(sorted_df, cumul_columns)

    # Check that the new dataframe with all dates does not contain errors
    errors = check_inconsistencies(full_df, cumul_columns, fillna=True)

    for col in cumul_columns:
        full_df[col] = full_df[col].astype(int)
    
    full_df['date'] = pd.to_datetime(full_df['date'], format='%Y-%m-%d')
    
    # Drop the last day since the reports have probably not all come in
    full_df=full_df[:-27]
    
    return full_df


def check_inconsistencies(df, columns, fillna=False, verbose=False):
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
    cantons = df['canton'].unique()
    inconsistencies = []
    for col_name in columns:
        for canton in cantons:
            has_value = False
            max_value = 0.
            for index in df[df['canton'] == canton][col_name].index:
                if not has_value:
                    if np.isnan(df.loc[index, col_name]):
                        if fillna:
                            df.loc[index, col_name] = max_value
                    else:
                        has_value = True
                        max_value = df.loc[index, col_name]
                else:
                    if np.isnan(df.loc[index, col_name]):
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
        if not df.loc[df['canton'] == canton_name, 'date'].is_unique:
            inc.append(canton_name)

    if len(inc) > 0:
        print("{} cantons have same day reports.".format(len(inc)))
    else:
        print("No cantons have same day reports.")

    return inc


def make_new_df(df, cumul_columns):
    """
    Create a full dataframe of all cumulative columns. This function assumes no
    reports means no change.

    Parameters
    ----------
    df : pandas DataFrame
        DataFrame object obtained from reading the raw Covid-19 database.
    cumul_columns : list
        List of cumulative column names.

    Returns
    -------
    full_df : pandas DataFrame
        Preprocessed pandas DataFrame.

    """
    
    min_date = df.date.min()
    max_date = df.date.max()
    cols = ['date', 'canton']
    cols.extend(cumul_columns)
    date_range = pd.date_range(min_date, max_date)
    
    full_df = pd.DataFrame(
        index=range(len(date_range) * len(df['canton'].unique())),
        columns=cols)

    list_of_dates = []
    for i in date_range:
        list_of_dates.extend([str(i)[0:10]] * len(df['canton'].unique()))
    
    full_df.date = pd.Series(list_of_dates)

    canton_series = pd.Series(df['canton'].unique())
    full_df.canton = pd.concat([canton_series] * len(date_range),
                               ignore_index=True)

    for index in df.index:
        row = df.loc[index]
        canton = row['canton']
        date = row['date']
        full_df_id = full_df[
            full_df['canton'] == canton].loc[full_df.date == date].index[0]

        for col in cumul_columns:
            if not np.isnan(row[col]):
                full_df.loc[full_df_id, col] = row[col].astype(float)

    return full_df


def format_col(col_list):
    # Get a string instead of a list if there is only one column
    if len(col_list) == 1:
        return col_list[0]
    else:
        return col_list


def draw_plot(df, columns, cantons=None, exclude_FL=True, agg=True,
              remove_cumul=True, title=None, timeline=False, ax=None):
    """
    Function to draw the plots of a column of the pandas DataFrame. It gives us
    different options:
        - draw cantons separately instead of aggregating
        - exclude the Liechtenstein values (by default)
        - difference a cumulative column

    Major x-ticks occur every month start and minor ticks every Monday.

    Parameters
    ----------
    df : pd.DataFrame
        The preprocessed DataFrame of the Covid-19 database.
    columns : list
        List of columns of the dataframe we want to plot.
    cantons : list, optional
        List of canton abbreviations. The default is None (all cantons).
    exclude_FL : bool, optional
        Whether we want to exclude Liechtenstein. The default is True.
    agg : bool, optional
        Whether we want the sum of cantons. The default is True.
    remove_cumul : bool, optional
        Whether we remove cumulation. The default is True.
    title : string, optional
        Title of the plot. The default is None.
    timeline : bool, optional
        Whether we want to plot vertical lines of the timeline.
    ax : matplotlib.axes._subplots.AxesSubplot
        Matplotlib ax object in case we want to add to an existing plot.    

    Returns
    -------
    ax : matplotlib.axes._subplots.AxesSubplot
        Axes object that we plotted with.
    """
    
    if not ax:
        plt.figure()
        ax = plt.gca()
    
    if cantons is None:
        cantons = list(df['canton'].unique())
    
    if exclude_FL:
        df = df[df['canton'] != 'FL']
        if 'FL' in cantons:
            cantons.remove('FL')
    
    if len(columns) > 1:
        assert agg, "Can't plot multiple columns without aggregation"
    if len(cantons) > 1:
        assert len(columns) == 1 or agg, "Can't plot multiple columns for multiple cantons"
    
    if len(cantons) >= MAX_CANTONS and not agg:
        agg = True
        print("Forced aggregation, because there we are trying to plot more than {} cantons.".format(MAX_CANTONS))
    
    last_date = full_df['date'].max().strftime("%d %m %Y")
    
    if agg:
        if remove_cumul:
            df[df['canton'].isin(cantons)].groupby(
                by='date').sum()[columns].diff().fillna(0).plot(ax=ax)
        else:
            df[df['canton'].isin(cantons)].groupby(
                by='date').sum()[columns].plot(ax=ax)
    
    else:
        if remove_cumul:
            for canton in cantons:
                x = df[df['canton'] == canton][columns].diff().fillna(0)
                x.index = df[df['canton'] == canton]['date'].values
                line, = ax.plot(x.index, x[columns])
                line.set_label(canton)
        else:
            for canton in cantons:
                x = df[df['canton'] == canton][columns]
                x.index = df[df['canton'] == canton]['date'].values
                line, = ax.plot(x.index, x[columns])
                line.set_label(canton)
    
    if not title:
        title = ''
        if agg:
            title += 'Sum of '
        if remove_cumul:
            title += 'diffed {} '.format(format_col(columns))
        else:
            title += 'cumulative {} '.format(format_col(columns))
        title = title.capitalize()
        if len(cantons) == 26 and exclude_FL:
            title += 'for Switzerland until {}'.format(last_date)
        elif len(cantons) == 27:
            title += 'for CH and FL until {}'.format(last_date)
        elif len(cantons) < MAX_CANTONS:
            title += 'of cantons {} until {}'.format(cantons, last_date)
        else:
            title += 'for {} cantons until {}'.format(len(cantons), last_date)
    
    ax.set_title(title)
    ax.set_xlabel('')
    
    if timeline:
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width*0.9, box.height])
        ax.axvline(x=pd.to_datetime('02-28-20'), color='r', alpha=0.8,
                   ls='--', label='Ban events > 1000')
        ax.axvline(x=pd.to_datetime('03-13-20'), color='g', alpha=0.8,
                   ls='--', label='Ban > 100 & close schools')
        ax.axvline(x=pd.to_datetime('03-16-20'), color='m', alpha=0.8,
                   ls='--', label='Close bars and shops')
        ax.axvline(x=pd.to_datetime('04-27-20'), color='r', alpha=0.8,
                   ls='-', label='Reopen dentists, hairdressers...')
        ax.axvline(x=pd.to_datetime('05-11-20'), color='g', alpha=0.8,
                   ls='-', label='Reopen schools and shops')
        ax.axvline(x=pd.to_datetime('07-06-20'), color='m', alpha=0.8,
                   ls='-', label='Masks in public transport')
        
        ax.legend(loc='lower right', bbox_to_anchor=(1.2, 0.5), fancybox=True)
        
    return ax


def draw_example(full_df):
    fig, axes = plt.subplots(2, 2)
    
    draw_plot(full_df, ['ncumul_deceased'], cantons=['FR', 'VD'], exclude_FL=True,
              agg=False, remove_cumul=True, title=None, timeline=True,
              ax=axes[0, 0])

    draw_plot(full_df, ['ncumul_released'], cantons=None,
              exclude_FL=True, agg=True, remove_cumul=True, title=None,
              timeline=False, ax=axes[0, 1])
    
    draw_plot(full_df, ['ncumul_tested'], cantons=None, exclude_FL=False,
              agg=True, remove_cumul=False, title=None, timeline=False,
              ax=axes[1, 0])

    draw_plot(full_df, ['ncumul_conf'], cantons=None, exclude_FL=True,
              agg=True, remove_cumul=True, title=None, timeline=True,
              ax=axes[1, 1])


def draw_deceased(full_df, timeline=True, ax=None):
    draw_plot(full_df, ['ncumul_deceased'], timeline=timeline,
              title='Switzerland Covid-19 deaths', ax=ax)


def draw_confirmed(full_df, timeline=True, ax=None):
    draw_plot(full_df, ['ncumul_conf'], timeline=timeline,
              title='Switzerland Covid-19 new confirmed cases', ax=ax)

def draw_deceased_FR(full_df, timeline=True, ax=None):
    draw_plot(full_df, ['ncumul_deceased'], timeline=timeline, cantons=['FR'],
              title='Covid-19 deaths in canton FR', ax=ax)


def draw_confirmed_FR(full_df, timeline=True, ax=None):
    draw_plot(full_df, ['ncumul_conf'], timeline=timeline, cantons=['FR'],
              title='Covid-19 new confirmed cases in canton FR', ax=ax)


if __name__ == '__main__':
    plt.ion()
    matplotlib.interactive(True)
    full_df = preprocess('COVID19_Fallzahlen_CH_total.csv')
    
    fig, axes = plt.subplots(2, 1)
    
    draw_deceased(full_df, ax=axes[0])
    draw_confirmed(full_df, ax=axes[1])

    plt.show(block=True)
