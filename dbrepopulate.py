from datetime import datetime
import os
import pandas as pd
import sys
import psycopg2


def clean_pbp(walk_directory):
    '''
    Function takes in a dataframe and turns NA to integer 0 to fit with SQL
    database schema

    Inputs:
    df - pandas dataframe

    Outputs:
    df - cleaned pandas dataframe
    '''

    def clean(df):

        col_names = ['coords_x', 'coords_y', 'is_home', 'time_diff',
                     'shot_angle', 'distance', 'event_length', 'game_seconds',
                     'home_corsi', 'away_corsi', 'home_corsi_total',
                     'away_corsi_total']

        for column in col_names:
            df[column] = df[column].fillna(0).astype(int)

        return df

    for path, subdir, files in os.walk(walk_directory):
        for dirs in subdir:
            try:

                # opens nhl pbp csv for importing
                pbp_df = pd.read_csv('{}/{}/{}'.format(path, dirs, dirs),
                                     sep='|')

                # clean NA's from integer columns and writes to | delim file
                cleaned_df = clean(pbp_df)

                cleaned_df.to_csv('{}/{}/{}'.format(path, dirs, dirs),
                                  sep='|', index=False)

            except Exception:
                print('{}/{}/{} file not found'.format(path, dirs, dirs))


def stats_compile(file_name, walk_directory, database):
    with open(file_name, 'w') as master_stats_file:
        x = 0
        for path, subdir, files in os.walk(walk_directory):
            for dirs in subdir:
                try:
                    if database == 'masternhlpbp':
                        with open('{}/{}/{}'.format(path, dirs, dirs), 'r',
                                  encoding="utf-8") as game_stats:
                            header = next(game_stats)
                            if x == 0:
                                master_stats_file.write(header)
                            master_stats_file.writelines(
                                                         game_stats.
                                                         readlines())
                    else:
                        with open('{}/{}/{} {}'.format(path, dirs, dirs,
                                                       database), 'r',
                                  encoding="utf-8") as game_stats:
                            header = next(game_stats)
                            if x == 0:
                                master_stats_file.write(header)
                            master_stats_file.\
                                writelines(game_stats.readlines())
                except Exception:
                    pass
                x += 1
        print('{} master file written'.format(database))


def stats_sql_insert(cursor, connect, database, directory):
    for path, subdir, files in os.walk(directory):
        for dirs in subdir:
            try:
                if database == 'masternhlpbp':
                    with open('{}/{}/{}'
                              .format(path, dirs, dirs), 'r',
                              encoding="utf-8")\
                            as pbp:
                        sql = ('COPY {} FROM stdin WITH DELIMITER \'|\''
                               'CSV HEADER'.format(database))
                        cursor.copy_expert(sql, pbp)
                        connect.commit()
                elif database == 'goaliestats' or database == 'goaliestats5v5':
                    with open('{}/{}/{}'.format(path, dirs, database),
                              'r', encoding="utf-8")\
                                      as pbp:
                        sql = ('COPY {} FROM stdin WITH DELIMITER \'|\''
                               'CSV HEADER'.format(database))
                        cursor.copy_expert(sql, pbp)
                        connect.commit()

                else:
                    with open('{}/{}/{} {}'.format(path, dirs, dirs, database),
                              'r', encoding="utf-8")\
                                      as pbp:
                        sql = ('COPY {} FROM stdin WITH DELIMITER \'|\''
                               'CSV HEADER'.format(database))
                        cursor.copy_expert(sql, pbp)
                        connect.commit()

            except Exception as ex:
                print(ex)
                print('{} failed to insert'.format(dirs))
                connect.rollback()


def main():
    '''
    Inputs:
    sys.argv[1] - parent directory where folders are located to walk through
    and compile pbp data into one delim file

    Outputs:
    Stats files - total compiled stats in a text file for all the tables in the
    sql database for that season
    '''
    walk_directory = sys.argv[1]
    files_directory = sys.argv[2]

    # create postgresql connection
    conn = psycopg2.connect("host=localhost dbname=nhl user=matt")
    cur = conn.cursor()

    tables = ['masternhlpbp', 'playerstats', 'teamstats', 'playerstats5v5',
              'teamstats5v5', 'playerstatsadj', 'teamstatsadj',
              'playerstatsadj5v5', 'teamstatsadj5v5', 'goaliestats',
              'goaliestats5v5']
    start = datetime.now()
    seasons = ['2015', '2016', '2017', '2018']
    for season in seasons:
        clean_pbp('{}{}'.format(walk_directory, season))
        for table in tables:
            stats_sql_insert(cur, conn, table, '{}{}'.format(walk_directory,
                                                             season))
            stats_compile('{}{}/{}'.format(files_directory, season, table),
                          walk_directory, table)
    end = datetime.now()
    print(end - start)


if __name__ == '__main__':
    main()
