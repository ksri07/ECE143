#Processing file with utility functions better
#left out of the notebook to reduce clutter
import numpy as np
import pandas as pd
from functools import reduce
from os import path
###############
#ALL FILE PATHS RELATIVE TO THOSE IN GIT REPO,
#change this to change base data dir
base = 'data/'
###############



def statesTotals(showThirdParty=False):
    '''
    calculate the state totals of final election results
    in: None
    out: None
    '''
    df = pd.read_csv(base+'kaggle_data/president_county_candidate.csv')

    #each state will have a dictionary of candidates, where the keys are vote totals
    states = {k:dict() for k in df['state'].unique()}

    #first determine ALL candidates, then fetch parties (there is overlap sometimes)
    candidates = dict()
    for can in df['candidate'].unique():
        #assign candidate `can` their party affiliation
        candidates[can] = df[df['candidate'] == can].iloc[0]['party']

    #setup states dictionary
    for state in states.keys():
        for can in df[df['state'] == state]['candidate'].unique():
            #initialize every states vote total to 0 for each cadidate,party pair
            states[state][(can,candidates[can])] = 0

    #match column names with kaggle data for consistency
    #now tally up votes for each candidate by state
    for state in states.keys():
        for can,par in states[state].keys():
            states[state][(can,par)] = (df[ (df['state']==state) & (df['candidate']==can) & (df['party']==par)]['total_votes'].sum())
   
    #unpack and convert dictionary
    ret = dict()
    ret = {k:[] for k in ['state','candidate','party','total_votes']}
    for state in states.keys():
        thirdCount = 0
        for key in states[state].keys():
            if not showThirdParty and not(key[1]=="REP" or key[1]=="DEM"):
                thirdCount+=states[state][key]
            else:
                ret['state'].append(state)
                ret['candidate'].append(key[0])
                ret['party'].append(key[1])
                ret['total_votes'].append(states[state][key])
        #at the of each state, fill in third party if needed
        if not showThirdParty:
            ret['state'].append(state)
            ret['candidate'].append("Other")
            ret['party'].append("N/A")
            ret['total_votes'].append(thirdCount)

    return pd.DataFrame(ret)

def readPreElectionPolls():
    '''
    reads the pre election polling data, joining into single table
    in: None
    out:None
    '''
    #file names
    pollsters = ['Emerson','Marist','Monmouth','Siena','SurveyMonkey']
    candidates = ['Biden','Trump']
    dfs = []
    #read files into df list
    for poll in pollsters:
        for can in candidates:
            dfs.append(pd.read_csv(base+'pre_election_polls/'+poll+'_'+can.lower()+'.csv'))
            dfs[-1]['Candidate'] = can
            dfs[-1]['Pollster'] = poll
    #combine to one dataframe, sort
    df  = pd.concat(dfs).sort_values(by=['State','Candidate','Pollster'])
    #get rid of codes
    df['State'] = df['State'].replace(stateDict())
    #reindex
    df = df.reset_index(drop=True)
    return df

def readPostElectionPolls():
    '''
    reads the post election polling data
    in: None
    out:None
    '''
    #file names
    pollsters = ['Edison']
    candidates = ['Biden','Trump']
    dfs = []
    #read files into df list
    for poll in pollsters:
        for can in candidates:
            dfs.append(pd.read_csv(base+'post_election_polls/'+poll+'_'+can.lower()+'.csv'))
            dfs[-1]['Candidate'] = can
            dfs[-1]['Pollster'] = poll
    #combine to single df and sort
    df  = pd.concat(dfs).sort_values(by=['State','Candidate','Pollster'])
    #get rid of codes
    df['State'] = df['State'].replace(stateDict())
    #reindex
    df = df.reset_index(drop=True)
    return df

def stateDict(useShortKey=True):
    '''
    generate state dictionaries for conversion from code to long string
    in: useShortKey, bool - if true, state code is key and name is value,
        otherwise it is flipped
    out: dictionary of state:code paris
    '''

    df = pd.read_csv(base+'state_abbrev.csv')

    if useShortKey:
        return pd.Series(df['State'].values,index=df['Code']).to_dict()
    else:
        return pd.Series(df['Code'].values,index=df['State']).to_dict()

def calculatePrePostDifferences(dfPost,dfPre):
    '''
    generate catagorical differences from polling data each numeric column
    will be POSTELECTIONValue - PREELECTIONValue
    so, a positive value means the value increased for the respective candidate
    in: postPolls - df of post election polls (from readPostPolls)
        prePolls - df of post election polls (from readPrePolls)
    out: df containing info
    '''
    ##As is this function is built to only take in a single of post pollster
    ##as this is all we have, appropriate preprocessing in ther manner done for
    ##pre pollsters should be done if additional post pollsters are added

    assert isinstance(dfPost,pd.DataFrame) and isinstance(dfPre,pd.DataFrame)

    #assert ensures that there is only one pollster for post
    assert  dfPost['Pollster'].unique() == ['Edison']
    #if this fails you must add another loop for Post Pollsters in the `organize and subtract` section

    print('Generating differences.csv..',end='',)
    #setup new df
    dfRet = pd.DataFrame(columns=dfPre.columns)
    dfRet = dfRet.drop(columns=['Pollster'])
    dfRet.insert(len(dfRet.columns),'Pre Pollster',None)
    dfRet.insert(len(dfRet.columns),'Post Pollster',None)
    
    #get numeric columns for subtraction
    stringCols = ['Candidate','Pollster','State']
    numericColumns = list(set(list(dfPre.columns)) - set(stringCols))

    
    #organize and subtract
    dfs = []
    for p in dfPre['Pollster'].unique():
        print('.',end='',flush=True)
        for state in dfPre['State'].unique():
            if (not (state in dfPre[dfPre['Pollster']==p]['State'].unique())) or (not (state in dfPost['State'].unique())):
                continue
            for can in dfPre['Candidate'].unique(): 
                temp = dfPre[(dfPre['Candidate']==can) & (dfPre['State']==state) & (dfPre['Pollster']==p)][numericColumns]
                oTemp = dfPost[(dfPost['Candidate']==can) & (dfPost['State']==state)][numericColumns]
                temp =  oTemp.reset_index(drop=True) - temp.reset_index(drop=True)
                temp['Candidate'] = can
                temp['State'] = state
                temp['Pre Pollster'] = p
                temp['Post Pollster'] = 'Edison'
                dfs.append(temp)

    dfRet = pd.concat(dfs)
    #for order
    dfRet = dfRet.reindex(columns=['State','Male','Female','Black','Hispanic/Latino','White + BA/BS','White + No BA/BS','Republican','Democrat','Independent','65+','Candidate','Pre Pollster','Post Pollster'])
    dfRet = dfRet.reset_index(drop='True')
    dfRet.to_csv(base+'differences.csv')

    

def getPrePostDifferences(prePollsters=None):
    '''
    check if the differences CSV exists and if not generate it and read it into df
    in: prePollsters, a list of strings indicating which pollsters to use
        if None, then all available are used
        alternatively, the user can remove items from pre/post polls if they
        wish for them not to be included

    '''
    if not path.exists(base+'differences.csv'):
        print("Processing..",flush=True)
        calculatePrePostDifferences(readPostElectionPolls(),readPreElectionPolls())
        print('done')
    
    df = pd.read_csv(base+'differences.csv',index_col=0)


    if not prePollsters is None:
        assert all((p in df['Pollster'].unique()) for p in prePollsters)
        df = df[df['Pollsters'].isin(prePollsters)]
   
    return df

