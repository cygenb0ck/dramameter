# reproduce pandas bug
import pandas
import dateutil.parser
import matplotlib.pyplot as plt

p_vals = {
    'x_vals' : [
        "2006-12-17 00:00:00+01:00",
        "2006-12-18 00:00:00+01:00",
        "2006-12-19 00:00:00+01:00",
        "2006-12-20 00:00:00+01:00",
        "2006-12-21 00:00:00+01:00",
        "2006-12-22 00:00:00+01:00",
        "2006-12-23 00:00:00+01:00",
        "2006-12-24 00:00:00+01:00",
        "2006-12-25 00:00:00+01:00",
        "2006-12-26 00:00:00+01:00",
    ],
    'y_vals' : [
        10,9,8,7,6,5,4,3,2,1
    ]
}

p_vals2 = {
    'x_vals' : [
        "2006-12-17 00:00:00+01:00",
        "2006-12-18 00:00:00+01:00",
        "2006-12-19 00:00:00+01:00",
        "2006-12-20 00:00:00+01:00",
        "2006-12-21 00:00:00+01:00",
    ],
    'y_vals' : [
        1,2,3,4,5
    ]
}

p_vals['x_vals'] = [ dateutil.parser.parse(x) for x in p_vals['x_vals'] ]
p_vals2['x_vals'] = [ dateutil.parser.parse(x) for x in p_vals2['x_vals'] ]

df = pandas.DataFrame(data = [1,2,3,4,5], index=["2006-12-17","2006-12-18","2006-12-19","2006-12-20","2006-12-21"])
df.index = pandas.to_datetime(df.index, format="%Y-%m-%d")

fig, ax1 = plt.subplots()
ax2 = ax1.twinx()

ax1.plot(p_vals['x_vals'], p_vals['y_vals'], color="r")
#ax2.plot(p_vals2['x_vals'], p_vals2['y_vals'], color="b") # works as intended
df.plot(ax=ax2, color="b") # hides data on ax1

plt.show()

# column_descriptor = ('Wien Hohe Warte','48,2486','16,3564','198.0','Anhöhe','Ebene','Lufttemperatur','Lufttemperatur um 14 MEZ (°C)')
#
# '''
# the transposed file was createdin the following way
# df = pandas.read_csv(in_file, skiprows=4, encoding='iso-8859-1', delimiter=';')
# df = df.transpose()
# df.to_csv(out_file)
# '''
#
# df1 = pandas.read_csv("./zamg_data/2006_ZAMG_Jahrbuch_transposed.csv", header=[1,2,3,4,5,6,7,8], index_col=0, decimal=',')
# df1.index = pandas.to_datetime( df1.index, format="%d.%m.%Y" ).tz_localize("CET")
#
#
# df1_by_col = df1.loc[:, column_descriptor]
#
# df1_by_col_by_index = df1_by_col.loc[(df1_by_col.index >= p_vals['x_vals'][0]) & (df1_by_col.index <= p_vals['x_vals'][-1])]
#
# fig, ax1 = plt.subplots()
# ax2 = ax1.twinx()
#
# ax1.plot(p_vals['x_vals'], p_vals['y_vals'], color="r")
#
# df1_by_col.plot(ax=ax2, color="b") # THIS WORKS
# #df1_by_col_by_index.plot(ax=ax2) # THIS HIDES
#
# plt.show()


