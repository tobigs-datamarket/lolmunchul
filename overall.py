import requests
import json
import time
import pandas as pd
from urllib import parse
import pprint as pp
import numpy as np
from itertools import product
import math

import warnings
warnings.filterwarnings(action='ignore')

class overall:
    def __init__(self, apiKey, matchId) -> None:
        self.apiKey = apiKey
        self.matchId = matchId

    def make_damagestat_row(self, participantlist, timestamp, c): #데미지 관련 데이터 프레임 만들기
        final_frame=pd.DataFrame()
        for i in participantlist:
            value_1=pd.DataFrame(c['info']['frames'][timestamp]['participantFrames'][i]['damageStats'].values()).T
            value_1.columns=c['info']['frames'][timestamp]['participantFrames'][i]['damageStats'].keys()
            value_2=pd.DataFrame(c['info']['frames'][timestamp]['participantFrames'][i]['position'].values()).T
            value_2.columns=c['info']['frames'][timestamp]['participantFrames'][i]['position'].keys()
            total_value=pd.concat([value_1,value_2],axis=1)
            total_value['participantId']=c['info']['frames'][timestamp]['participantFrames'][i]['participantId']
            total_value['timestamp']=timestamp
            final_frame=pd.concat([final_frame,total_value])
        return final_frame #데미지 스탯, 포지션, 타임스탬프, 참여자 아이디 열 생성
    
    def calculate_dpm(self, df): 
        df['DPM'] = df.groupby('participantId')['totalDamageDoneToChampions'].diff()
        df['DPM-D'] = 0

        for _, row in df.iterrows():
            participant_id = row['participantId']
            #다른 팀의 같은 포지션 참여자 아이디 부여
            opponent_id = participant_id + 5 if participant_id <= 5 else participant_id - 5
            #상대방의 DPM
            opponent_dpm = df.loc[(df['participantId'] == opponent_id) & (df['timestamp'] == row['timestamp']), 'DPM']
            #dpm_diff = 해당 플레이어의 DPM - 동일한 포지션의 참여자의 DPM
            if not opponent_dpm.empty:
                dpm_diff = row['DPM'] - opponent_dpm.iloc[0]
                if dpm_diff > 0:
                    df.loc[(df['participantId'] == participant_id) & (df['timestamp'] == row['timestamp']), 'DPM-D'] = dpm_diff
                    df.loc[(df['participantId'] == opponent_id) & (df['timestamp'] == row['timestamp']), 'DPM-D'] = -dpm_diff
        df.fillna(0,inplace=True)
        return df
    #KDA = (kills + Assists)/deaths . 데스가 0일 경우에 그냥 K+A.
    def calculate_kda(self, dataframe):
        dataframe['kda'] = (dataframe['kills'] + dataframe['assists']) / dataframe['deaths']
        dataframe.loc[dataframe['deaths'] == 0, 'kda'] = dataframe['kills'] + dataframe['assists']
        return dataframe
    
    def calculate_kill_proportion(self, dataframe):
        # Sort the dataframe by timestamp and participantIds
        dataframe.sort_values(['timestamps', 'participantIds'], inplace=True)

        # Group the dataframe by timestamp
        grouped = dataframe.groupby('timestamps')

        team1_mask = dataframe['participantIds'].between(1, 5)
        team2_mask = dataframe['participantIds'].between(6, 10)
        #Kill proportion = kills / total kills of the team where the player belongs to
        dataframe['team1_kills'] = grouped['kills'].transform(lambda x: np.sum(x[team1_mask]))
        dataframe['team2_kills'] = grouped['kills'].transform(lambda x: np.sum(x[team2_mask]))

        # Calculate the kill proportion for each player in their team
        dataframe['kp'] = np.where(team1_mask, dataframe['kills'] / dataframe.groupby('timestamps')['team1_kills'].transform('sum'),
                                dataframe['kills'] / dataframe.groupby('timestamps')['team2_kills'].transform('sum'))

        return dataframe
    
    def info(self, req,partition_list):
        cs=list()
        gold=list()
        xp=list()
        for i in range(len(req.json()['info']['frames'])):
            for j in partition_list:
                cs.append(req.json()['info']['frames'][i]['participantFrames'][j]['minionsKilled'])
                gold.append(req.json()['info']['frames'][i]['participantFrames'][j]['totalGold'])
                xp.append(req.json()['info']['frames'][i]['participantFrames'][j]['xp'])
                cs_df=pd.DataFrame(cs,columns=['Cs'])
                gold_df=pd.DataFrame(gold,columns=['Gold'])
                xp_df=pd.DataFrame(xp,columns=['Xp'])
                info=pd.concat([cs_df,gold_df,xp_df],axis=1)

        return info
    
    def is_point_above_line(self, x, y, x1, y1, x2, y2):
        slope = (y2 - y1) / (x2 - x1) if (x2 - x1) != 0 else float('inf')
        y_intercept = y1 - slope * x1
        return y >= slope * x + y_intercept

    def is_point_below_line(self, x, y, x1, y1, x2, y2):
        slope = (y2 - y1) / (x2 - x1) if (x2 - x1) != 0 else float('inf')
        y_intercept = y1 - slope * x1
        return y <= slope * x + y_intercept
    
    def eventWard(self, json):
        df = pd.DataFrame(columns=['killerId', 'creatorId', 'timestamp', 'type','wardType'])
        for time in range(1, len(json['info']['frames'])): # for each frame
            event = pd.DataFrame(json['info']['frames'][time]['events'])
            try:
                df = pd.concat([df, event[event['type'] == 'WARD_KILL'][['killerId', 'timestamp', 'type','wardType']]])
                df = pd.concat([df, event[event['type'] == 'WARD_PLACED'][['creatorId', 'timestamp', 'type', 'wardType']]])
            except:
                pass
        df = df.fillna(0) # NaN to 0
        df['participantId'] = df['killerId'] + df['creatorId']
        df = df[['participantId', 'timestamp', 'type', 'wardType']]
        df.sort_values(by='timestamp')
        return df
    
    def make_dpm_df(self, timestamp,partition_list,c):
        total_df=pd.DataFrame()
        for i in range(timestamp):
            participant=self.make_damagestat_row(partition_list,i,c)
            total_df=pd.concat([total_df,participant])
        dpm_df = total_df.copy()
        dpm_df = self.calculate_dpm(dpm_df)
        return dpm_df
    
    def make_merged_df(self,c,req):
        participant_ids=[]
        for i in range(len(c['info']['participants'])):
            participant_ids.append(c['info']['participants'][i]['participantId'])
        frame_df = pd.DataFrame(c['info']['frames'])

        EMK=[]
        for i in range(len(req.json()['info']['frames'])):
            for j in range(len(req.json()['info']['frames'][i]['events'])):
                if req.json()['info']['frames'][i]['events'][j]['type']=='CHAMPION_KILL':
                    EMK.append(req.json()['info']['frames'][i]['events'][j])

        EMK_df = pd.DataFrame(EMK)
        EMK_df['timestamp']= EMK_df['timestamp']//60000

        frame_df['timestamp']=frame_df['timestamp']//60000

        player_dicts = {}
        players = range(1,11)
        timestamps = EMK_df['timestamp'].unique()

        for player in players:
            player_dict = {}
            for timestamp in timestamps:
                player_dict[timestamp] = 0
            player_dicts[player] = player_dict

        for _, row in EMK_df.iterrows():
            assisting_ids = row['assistingParticipantIds']
            timestamp = row['timestamp']
            if isinstance(assisting_ids, list):
                for player_id in assisting_ids:
                    player_dicts[player_id][timestamp] += 1

        assist_df = pd.DataFrame.from_dict(player_dicts) # Convert player_dicts to a DataFrame

        assist_df = pd.DataFrame.from_dict(player_dicts)
        assist_df = assist_df.rename_axis('timestamps').reset_index()  # Rename the index column as 'timestamps'
        assist_df = assist_df.melt(id_vars='timestamps', var_name='ParticipantIds', value_name='assists')
        assist_df['ParticipantIds'] = assist_df['ParticipantIds'].astype(int)# Convert the 'ParticipantIds' column to integer type
        assist_df = assist_df.sort_values(['timestamps','ParticipantIds'])
        assist_df['assists'] = assist_df.groupby('ParticipantIds')['assists'].cumsum()# Cumulate the assists by participantIds
        assist_df = assist_df.reset_index(drop=True)

        kill_dicts = {}
        players = range(1, 11)
        timestamps = EMK_df['timestamp'].unique()

        for player in players:
            kill_dicts[player] = {}
            for timestamp in timestamps:
                kill_dicts[player][timestamp] = 0

        for _, row in EMK_df.iterrows():
            kill_ids = row['killerId']
            timestamp = row['timestamp']

            if kill_ids in players:
                kill_dicts[kill_ids][timestamp] += 1

        kill_df = pd.DataFrame.from_dict(kill_dicts)

        kill_df = kill_df.rename_axis('timestamps').reset_index()  # Rename the index column as 'timestamps'
        kill_df = kill_df.melt(id_vars='timestamps', var_name='ParticipantIds', value_name='kills')
        kill_df['ParticipantIds'] = kill_df['ParticipantIds'].astype(int)# Convert the 'ParticipantIds' column to integer type
        kill_df = kill_df.sort_values(['timestamps','ParticipantIds'])
        kill_df['kills'] = kill_df.groupby('ParticipantIds')['kills'].cumsum()# Cumulate the kills by participantIds
        kill_df = kill_df.reset_index(drop=True)

        death_dicts = {}
        players = range(1, 11)
        timestamps = EMK_df['timestamp'].unique()

        for player in players:
            death_dicts[player] = {}
            for timestamp in timestamps:
                death_dicts[player][timestamp] = 0

        for _, row in EMK_df.iterrows():
            death_ids = row['victimId']
            timestamp = row['timestamp']

            if death_ids in players:
                death_dicts[death_ids][timestamp] += 1

        death_df = pd.DataFrame.from_dict(death_dicts)
        death_df = death_df.rename_axis('timestamps').reset_index()  # Rename the index column as 'timestamps'
        death_df = death_df.melt(id_vars='timestamps', var_name='ParticipantIds', value_name='deaths')
        death_df['ParticipantIds'] = death_df['ParticipantIds'].astype(int)# Convert the 'ParticipantIds' column to integer type
        death_df = death_df.sort_values(['timestamps','ParticipantIds'])
        death_df['deaths'] = death_df.groupby('ParticipantIds')['deaths'].cumsum()
        death_df = death_df.reset_index(drop=True)

        assist_df = assist_df.rename(columns={'ParticipantIds':'participantIds'})#rename ParticipandIds to participantIds in assist_df
        kill_df = kill_df.rename(columns={'ParticipantIds':'participantIds'})
        death_df = death_df.rename(columns={'ParticipantIds':'participantIds'})

        merged_df = assist_df.merge(kill_df, on=['timestamps', 'participantIds'], how='outer')# Merge assist_df and kill_df based on timestamps and participantIds
        merged_df = merged_df.merge(death_df, on=['timestamps', 'participantIds'], how='outer')# Merge the resulting DataFrame with death_df based on timestamps and participantIds
        kda_df = merged_df.copy()

        kda_df = self.calculate_kda(kda_df)
        kda_kp_df = self.calculate_kill_proportion(kda_df)
        kda_kp_df['kp'] = kda_kp_df['kp']*10

        sk_dicts = {}
        players = range(1,11)
        timestamps = EMK_df['timestamp'].unique()

        for player in players:
            sk_dicts[player] = {timestamp: 0 for timestamp in timestamps}


        #assistingPartiicpantIds를 탐색해, NaN이라면 해당 kill은 solo kill로 처리.
        #killerId를 통해 solo kill을 한 플레이어의 solo kill 수를 1 증가
        #soloKill이 아닌 경우에 대해, ParticipantId를 참고해 해당 player의 id가 있을 경우
        #해당 player의 assist 수를 1 증가
        
        
        for _, row in EMK_df.iterrows():
            assisting_ids = row['assistingParticipantIds']
            timestamp = row['timestamp']
            # check if assisting_ids contains NaN values
            if pd.Series(assisting_ids).apply(pd.isnull).any():
                sk_id = row['killerId']
                if sk_id ==0:
                    continue
                sk_dicts[sk_id][timestamp] += 1
        
        sk_df = pd.DataFrame.from_dict(sk_dicts)

        sk_df = sk_df.rename_axis('timestamps').reset_index()  # Rename the index column as 'timestamps'
        sk_df = sk_df.melt(id_vars='timestamps', var_name='ParticipantIds', value_name='soloKills')

        sk_df['ParticipantIds'] = sk_df['ParticipantIds'].astype(int)# Convert the 'ParticipantIds' column to integer type

        sk_df = sk_df.sort_values(['timestamps','ParticipantIds'])
        sk_df['soloKills'] = sk_df.groupby('ParticipantIds')['soloKills'].cumsum()
        sk_df = sk_df.reset_index(drop=True)

        sk_df = sk_df.rename(columns={'ParticipantIds':'participantIds'})#rename ParticipandIds to participantIds in sk_df
        med_fin_df = pd.merge(kda_kp_df, sk_df, on=['timestamps', 'participantIds'],how='left')#merge kdakp_df and sk_df on timestamps and participantIds
        before_df = med_fin_df.copy()

        timestamps = range(0, len(frame_df))
        participantIds = range(1,11)  # Assuming there are 10 participantIds
        all_combinations = list(product(timestamps, participantIds))
        all_combinations_df = pd.DataFrame(all_combinations, columns=['timestamps', 'participantIds'])

        merged_df = pd.merge(all_combinations_df, before_df, on=['timestamps', 'participantIds'], how='left')
        merged_df = merged_df.sort_values(['timestamps', 'participantIds'])
        merged_df = merged_df.groupby('participantIds').fillna(method='ffill')
        merged_df = merged_df.fillna(0)
        merged_df['timestamps'].value_counts()

        #add a column called participantIds which are the 반복 of 1 to 10 for each timestamp
        # Assuming merged_df is your DataFrame
        unique_timestamps = merged_df['timestamps'].unique()

        participant_ids = list(range(1, 11)) * len(unique_timestamps) # Create a list of participantIds ranging from 1 to 10 repeated for each timestamp
        merged_df['participantIds'] = participant_ids# Add the 'participantIds' column to the DataFrame
        merged_df = merged_df.sort_values(['timestamps', 'participantIds'])# Sort the DataFrame by 'timestamps' and 'participantIds'
        merged_df = merged_df[['timestamps', 'participantIds', 'kills','kda', 'assists', 'deaths', 'kp', 'soloKills','team1_kills','team2_kills']]
        merged_df.rename(columns={'participantIds':'participantId','timestamps':'timestamp'},inplace=True)
        return merged_df
    
    def FWD(self,timestamp,partition_list,c):
        damage_df=pd.DataFrame()
        for i in range(timestamp):
            participant=self.make_damagestat_row(partition_list,i,c)
            damage_df=pd.concat([damage_df,participant])

        count1,count2,count3,count4,count5,count6,count7,count8,count9,count10=0,0,0,0,0,0,0,0,0,0
        FWD=[]

        for i in range(len(damage_df['x'])):
            x = damage_df.iloc[i]['x']
            y = damage_df.iloc[i]['y']
            #고정
            x1, y1 = damage_df['x'].max(), 0
            x2, y2 = 0,damage_df['y'].max()

            # team red
            #player6
            if damage_df.iloc[i]['participantId']==6:
                if self.is_point_below_line(x, y, x1, y1, x2, y2):
                    count6+=1
                    FWD.append(round((count6/damage_df.iloc[i]['timestamp'])*100,2))
                else:
                    FWD.append(round((count6/damage_df.iloc[i]['timestamp'])*100,2))

            #player7
            elif damage_df.iloc[i]['participantId']==7:
                if self.is_point_below_line(x, y, x1, y1, x2, y2):
                    count7+=1
                    FWD.append(round((count7/damage_df.iloc[i]['timestamp'])*100,2))
                else:
                    FWD.append(round((count7/damage_df.iloc[i]['timestamp'])*100,2))

            #player 8
            elif damage_df.iloc[i]['participantId']==8:
                if self.is_point_below_line(x, y, x1, y1, x2, y2):
                    count8+=1
                    FWD.append(round((count8/damage_df.iloc[i]['timestamp'])*100,2))
                else:
                    FWD.append(round((count8/damage_df.iloc[i]['timestamp'])*100,2))

            #player9
            elif damage_df.iloc[i]['participantId']==9:
                if self.is_point_below_line(x, y, x1, y1, x2, y2):
                    count9+=1
                    FWD.append(round((count9/damage_df.iloc[i]['timestamp'])*100,2))
                else:
                    FWD.append(round((count9/damage_df.iloc[i]['timestamp'])*100,2))

            #player10
            elif damage_df.iloc[i]['participantId']==10:
                if self.is_point_below_line(x, y, x1, y1, x2, y2):
                    count10+=1
                    FWD.append(round((count10/damage_df.iloc[i]['timestamp'])*100,2))

                else:
                    FWD.append(round((count10/damage_df.iloc[i]['timestamp'])*100,2))


        #team blue
        #player1

            elif damage_df.iloc[i]['participantId']==1:
                if self.is_point_above_line(x, y, x1, y1, x2, y2):
                    count1+=1
                    FWD.append(round((count1/damage_df.iloc[i]['timestamp'])*100,2))
                else:
                    FWD.append(round((count1/damage_df.iloc[i]['timestamp'])*100,2))

            #player2
            elif damage_df.iloc[i]['participantId']==2:
                if self.is_point_above_line(x, y, x1, y1, x2, y2):
                    count2+=1
                    FWD.append(round((count2/damage_df.iloc[i]['timestamp'])*100,2))
                else:
                    FWD.append(round((count2/damage_df.iloc[i]['timestamp'])*100,2))

            #player3
            elif damage_df.iloc[i]['participantId']==3:
                if self.is_point_above_line(x, y, x1, y1, x2, y2):
                    count3+=1
                    FWD.append(round((count3/damage_df.iloc[i]['timestamp'])*100,2))
                else:
                    FWD.append(round((count3/damage_df.iloc[i]['timestamp'])*100,2))

            #player4
            elif damage_df.iloc[i]['participantId']==4:
                if self.is_point_above_line(x, y, x1, y1, x2, y2):
                    count4+=1
                    FWD.append(round((count4/damage_df.iloc[i]['timestamp'])*100,2))
                else:
                    FWD.append(round((count4/damage_df.iloc[i]['timestamp'])*100,2))

            #player5
            else:
                if self.is_point_above_line(x, y, x1, y1, x2, y2):
                    count5+=1
                    FWD.append(round((count5/damage_df.iloc[i]['timestamp'])*100,2))
                else:
                    FWD.append(round((count5/damage_df.iloc[i]['timestamp'])*100,2))



        FWD_df=pd.DataFrame(FWD,columns=['FWD'])
        FWD_df.fillna(0,inplace=True)
        return FWD_df
    
    def make_fwd_df(self,req,partition_list,timestamp,c):
        df1=self.info(req,partition_list)
        df2=self.FWD(timestamp,partition_list,c)
        df=pd.concat([df1,df2],axis=1)
        return df
    
    def make_ward_df(self,c): #한타 전후 지표 중 vision score 지표 생성 함수.
        ward=self.eventWard(c)
        ward['time']=ward['timestamp']//60000
        ward['new_type']=ward['type']+'_'+ward['wardType'];ward
        id_list=ward['participantId'].unique()
        time_list=ward['time'].unique()
        vsdf=pd.DataFrame(columns=['participantId','time','visionscore']) #참여자 아이디, 시간, visionscore 3개 열 생성
        for i in time_list:
            time=ward[ward['time']==i]
            for j in id_list:
                score=0
                id=time[time['participantId']==j]
                id.reset_index(inplace=True)
                score=0
                for k in range(len(id)): #와드 킬을 와드 설치보다 더 높은 점수 부여, 제어 와드인 경우, 가산점을 부과
                    if id['new_type'][k]=='WARD_KILL_YELLOW_TRINKET':
                        score=score+2
                    elif id['new_type'][k]=='WARD_KILL_CONTROL_WARD':
                        score=score+4
                    elif id['new_type'][k]=='WARD_KILL_SIGHT_WARD':
                        score=score+2
                    elif id['new_type'][k]=='WARD_KILL_BLUE_TRINKET':
                        score=score+2
                    elif id['new_type'][k]=='WARD_KILL_UNDIFINED':
                        score=score+2
                    elif id['new_type'][k]=='WARD_PLACED_YELLOW_TRINKET':
                        score=score+1
                    elif id['new_type'][k]=='WARD_PLACED_CONTROL_WARD':
                        score=score+3
                    elif id['new_type'][k]=='WARD_PLACED_SIGHT_WARD':
                        score=score+1
                    elif id['new_type'][k]=='WARD_PLACED_BLUE_TRINKET':
                        score=score+1
                    elif id['new_type'][k]=='WARD_PLACED_UNDIFINED':
                        score=score+1
                score_info = pd.DataFrame([[j, i, score]],columns = ['participantId','time','visionscore'])
                vsdf=pd.concat([vsdf,score_info])
        vsdf.rename(columns={'time':'timestamp'},inplace=True)
        vsdf.reset_index(drop=True,inplace=True)
        return vsdf
    
    def visionscore(self, visionscoreDf, timestamp) -> int:

        scoreDf = list()

        for i in range(0, 10): # 플레이어
            score = 0
            for j in range(i, timestamp*10, 10): # 이전 시간
                score+=int(visionscoreDf.iloc[j])
            scoreDf.append(score)
        return pd.DataFrame(scoreDf, columns=['visionScore'])
    
    def make_cc_df(self, c, timestamp, partition_list):
        CC=pd.DataFrame(columns=['participantId','time','CCScore'])
        for i in range(timestamp):
            for j in partition_list:
                score=c['info']['frames'][i]['participantFrames'][j]['timeEnemySpentControlled']
                score_info = pd.DataFrame([[j, i, score]],columns = ['participantId','time','CCScore'])
                CC=pd.concat([CC,score_info],axis=0)
        CC.reset_index(drop=True,inplace=True)

        return CC
    
    def merge_everything(self):
        url = 'https://asia.api.riotgames.com/lol/match/v5/matches/'+self.matchId+'/timeline?api_key='+self.apiKey
        req=requests.get(url)
        c = req.json()

        timestamp=len(c['info']['frames'])
        partition_list=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']

        dpm=self.make_dpm_df(timestamp,partition_list,c)
        kda=self.make_merged_df(c,req)
        fwd=self.make_fwd_df(req,partition_list,timestamp,c)
        ward=self.make_ward_df(c)
        cc = self.make_cc_df(c,timestamp,partition_list)
        
        all_df = pd.merge(left=dpm, right=kda, how='left', on=['participantId','timestamp'])
        all_df=pd.concat([all_df,fwd],axis=1)
        all_df=pd.concat([all_df,cc['CCScore']],axis=1)
        all_df = pd.merge(left=all_df, right=ward, how='left', on=['participantId','timestamp'])

        asiaUrl = 'https://asia.api.riotgames.com'
        v5_url = asiaUrl + '/lol/match/v5/matches/{}?api_key={}'  # matchid , api_key`
        url = v5_url.format(self.matchId ,self.apiKey)
        response = requests.get(url)
        match_data_v5 = response.json()

        df = pd.DataFrame(match_data_v5['info']['participants'])

        sample = df[['teamId','puuid','summonerName','participantId','teamPosition', 'challenges',
                'championName','lane','kills','deaths','assists','totalMinionsKilled','neutralMinionsKilled','goldEarned','goldSpent','champExperience','item0','item1','item2',
                'item3','item4','item5','item6','totalDamageDealt','totalDamageDealtToChampions','totalDamageTaken','damageDealtToTurrets','damageDealtToBuildings',
                'totalTimeSpentDead','visionScore','win','timePlayed']]
        
        new_df = sample[['teamId', 'summonerName', 'participantId', 'teamPosition', 'championName', 'lane']]
        new_df['teamId'] = np.where(new_df['teamId'] == 100, 'Red', 'Blue')
        all_df = pd.merge(left=all_df, right=new_df, how='left', on=['participantId'])
        all_df['visionscore'].fillna(0,inplace=True)
        all_df['match_id']=self.matchId

        return all_df