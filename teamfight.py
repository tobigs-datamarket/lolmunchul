import pandas as pd
import requests
from urllib import parse
import math

class teamFight:
    def __init__(self, apiKey, matchId) -> None:
        
        self.apiKey = apiKey
        self.matchId = matchId
        self.asiaUrl = 'https://asia.api.riotgames.com'

        timeLineUrl = self.asiaUrl + '/lol/match/v5/matches/' + self.matchId + '/timeline?api_key=' + self.apiKey
        r = requests.get(timeLineUrl)
        self.r = r.json()



    def euclideanDistance(self, x1, y1, x2, y2):
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    # construct champion kill df
    # return championKillDf, victimDamageDealtDf, victimDamageReceivedDf
    def detectTeamFight(self, champion_kill_df, interval_length=150000, max_kills=6, distance=500, teamfight_start_minute=15, teamfight_end_minute=20):
        # Sort the DataFrame by 'timestamp' column in ascending order
        champion_kill_df_sorted = champion_kill_df.sort_values('timestamp')
        
        # Initialize variables
        intervals = []
        teamfight_id_counter = 1
        
        # Keep track of the last end_minute
        last_end_minute = None
        
        # Iterate over the DataFrame starting from the first row
        for i in range(len(champion_kill_df_sorted)):
            row = champion_kill_df_sorted.iloc[i]
            timestamp = row['timestamp']
            
            # Look for the index of the last row within the current interval
            last_index = i + max_kills - 1
            if last_index >= len(champion_kill_df_sorted):
                break
            
            last_row = champion_kill_df_sorted.iloc[last_index]
            last_timestamp = last_row['timestamp']
            
            # Check if the interval length is within the threshold
            if last_timestamp - timestamp <= interval_length:
                # Get the subset of DataFrame within the current interval
                interval_df = champion_kill_df_sorted.iloc[i:last_index + 1]
                
                # Check for close positions of killed champions within the interval
                close_positions = False
                for _, row in interval_df.iterrows():
                    position_x = row['position_x']
                    position_y = row['position_y']
                    if self.euclideanDistance(position_x, position_y, interval_df['position_x'].mean(), interval_df['position_y'].mean()) <= distance:
                        close_positions = True
                        break
                
                # If there are close positions and the interval is within the desired time range, consider it a teamfight interval
                start_minute = math.floor(timestamp / 60000)
                end_minute = math.floor(last_timestamp / 60000)
                
                if start_minute == end_minute:
                    start_minute -= 1
                
                if teamfight_start_minute <= start_minute <= end_minute <= teamfight_end_minute:
                    # Check if the teamfight interval overlaps with the last one
                    if last_end_minute is None or start_minute > last_end_minute:
                        # Append the interval to the list
                        intervals.append({
                            'teamfightid': teamfight_id_counter,
                            'timestamp': timestamp,
                            'last_timestamp': last_timestamp,
                            'start_minute': start_minute,
                            'end_minute': end_minute,
                            'start_kill_id': row['kill_id'],
                            'end_kill_id': last_row['kill_id']
                        })
                        teamfight_id_counter += 1
                        
                        # Update the last_end_minute
                        last_end_minute = end_minute
        
        # Convert the list of dictionaries to a DataFrame
        result_df = pd.DataFrame(intervals)
        
        return result_df

    def championKillDf(self):
        frames = self.r['info']['frames']

        # Initialize empty lists to store the collected data
        champion_kill_data = []
        victim_damage_dealt_data = []
        victim_damage_received_data = []

        # Initialize a counter for the kill ID
        kill_id_counter = 1

        # Iterate over the frames
        for i in range(len(frames)):
            events = frames[i]['events']
            # Iterate over the events in each frame
            for event in events:
                if event['type'] == "CHAMPION_KILL": # event type이 CHAMPION_KILL일 때

                    try:
                        assisting_ids = event['assistingParticipantIds']
                    except KeyError:
                        assisting_ids = []

                    champion_kill_data.append({
                        'kill_id': kill_id_counter,
                        'assistingParticipantIds': assisting_ids,
                        #'bounty': event['bounty'],
                        #'killStreakLength': event['killStreakLength'],
                        'killerId': event['killerId'],
                        'position_x': event['position']['x'],
                        'position_y': event['position']['y'],
                        'timestamp': event['timestamp'],
                        'victimId': event['victimId'],
                        'minute' : math.floor(event['timestamp']/60000) # 새로 추가함
                    })
                    kill_id_counter += 1

                    if 'victimDamageDealt' in event:
                        damage_dealt = event['victimDamageDealt']
                        for damage in damage_dealt:
                            victim_damage_dealt_data.append({
                                'kill_id': kill_id_counter,
                                'participantId': event['victimId'],
                                'damageType': damage['type'],
                                'damageName': damage['name'],
                                'spellName': damage['spellName'],
                                'spellSlot': damage['spellSlot'],
                                'physicalDamage': damage['physicalDamage'],
                                'magicDamage': damage['magicDamage'],
                                'trueDamage': damage['trueDamage'],
                                'basicAttack': damage['basic']
                            })
                    if 'victimDamageReceived' in event:
                        damage_received = event['victimDamageReceived']
                        for damage in damage_received:
                            victim_damage_received_data.append({
                                'kill_id': kill_id_counter,
                                'participantId': event['victimId'],
                                'damageType': damage['type'],
                                'damageName': damage['name'],
                                'spellName': damage['spellName'],
                                'spellSlot': damage['spellSlot'],
                                'physicalDamage': damage['physicalDamage'],
                                'magicDamage': damage['magicDamage'],
                                'trueDamage': damage['trueDamage'],
                                'basicAttack': damage['basic']
                            })

        # Create DataFrames from the collected data
        champion_kill_df = pd.DataFrame(champion_kill_data)
        victim_damage_dealt_df = pd.DataFrame(victim_damage_dealt_data)
        victim_damage_received_df = pd.DataFrame(victim_damage_received_data)

        return champion_kill_df, victim_damage_dealt_df, victim_damage_received_df

    

    def winnerTeamFight(self, team, startPoint, endPoint) -> int:
        # teamFightTime = detect_high_kill_intervals(champion_kill_df)

        # 한타를 하는 이유: 한타를 통해 이득을 얻고자 하기 위함
        # 한타 승패 -> 한타가 끝났을 때 누가 이득을 봤느냐에 따라 승패가 나뉜다고 생각함
        # 기본적인 경우: 한타가 끝났을 때 살아남은 인원 수가 많은 팀이 이긴다.(확실하진 않다. 오브젝트 싸움의 경우 살아남은 인원이 2:1이더라도 장로 드래곤 or 바론 먹으면 이긴거니까?)
        # 그래서 생각한 점: 한타 전 후로 골드를 비교해서 골드를 더 많이 번 팀이 이긴다?
        earnedGoldBlue = sum([self.r['info']['frames'][endPoint]['participantFrames'][str(_)]['totalGold'] for _ in range(1, 6)]) - sum([self.r['info']['frames'][startPoint]['participantFrames'][str(_)]['totalGold'] for _ in range(1, 6)])
        earnedGoldRed = sum([self.r['info']['frames'][endPoint]['participantFrames'][str(_)]['totalGold'] for _ in range(6, 11)]) - sum([self.r['info']['frames'][startPoint]['participantFrames'][str(_)]['totalGold'] for _ in range(6, 11)])

        if (earnedGoldBlue > earnedGoldRed) & (team == 100) :

            return 1
        elif (earnedGoldBlue > earnedGoldRed) & (team == 200):
            return 0
        elif (earnedGoldBlue < earnedGoldRed) & (team == 100):
            return 0
        elif (earnedGoldBlue < earnedGoldRed) & (team == 200):
            return 1
        else:
            return 2

        # else: # 두 팀이 번 골드가 같은 경우(거의 그럴 일 없겠지만)
        #     raise ValueError("어떻게 골드가 같을 수 있죠?")

        
    def teamFightDamageStats(self, startPoint, endPoint, participantId):

        frames = self.r['info']['frames']

        damageBeforeFight = frames[startPoint]['participantFrames'][participantId]['damageStats']['totalDamageDoneToChampions']
        damageAfterFight = frames[endPoint]['participantFrames'][participantId]['damageStats']['totalDamageDoneToChampions']
        damageStats = damageAfterFight - damageBeforeFight
        
        return damageStats

    def teamFightCCScores(self, startPoint, endPoint, participantId):

        frames = self.r['info']['frames']

        ccScoreBeforeFight = frames[startPoint]['participantFrames'][participantId]['timeEnemySpentControlled']
        ccScoreAfterFight = frames[endPoint]['participantFrames'][participantId]['timeEnemySpentControlled']
        ccScoreStats = ccScoreAfterFight - ccScoreBeforeFight

        return ccScoreStats
        
    def teamFightReceivedDamageStats(self, startPoint, endPoint, participantId):

        frames = self.r['info']['frames']
        ReceivedDamageBeforeFight = frames[startPoint]['participantFrames'][participantId]['damageStats']['totalDamageTaken']
        ReceivedDamageAfterFight = frames[endPoint]['participantFrames'][participantId]['damageStats']['totalDamageTaken']
        ReceivedDamageStats = ReceivedDamageAfterFight - ReceivedDamageBeforeFight
        
        return ReceivedDamageStats
    
    def extractTeamFightStats(self, startPoint, endPoint):
        # matchId teamId SummonerName Champion Lane SpecificLane SpecificIndex Win/Lose
        
        v5_url = self.asiaUrl + '/lol/match/v5/matches/{}?api_key={}'  # matchid , api_key`
        url = v5_url.format(self.matchId ,self.apiKey)
        response = requests.get(url)
        match_data_v5 = response.json()

        df = pd.DataFrame(match_data_v5['info']['participants'])

        sample = df[['teamId','puuid','summonerName','participantId','teamPosition', 'challenges', 
            'championName','lane','kills','deaths','assists','totalMinionsKilled','neutralMinionsKilled','goldEarned','goldSpent','champExperience','item0','item1','item2',
            'item3','item4','item5','item6','totalDamageDealt','totalDamageDealtToChampions','totalDamageTaken','damageDealtToTurrets','damageDealtToBuildings',
            'totalTimeSpentDead','visionScore','win','timePlayed']]
        
        challenge = pd.DataFrame(sample['challenges'].tolist())

        col = challenge[['soloKills','abilityUses','damageTakenOnTeamPercentage','skillshotsDodged','skillshotsHit','enemyChampionImmobilizations','laneMinionsFirst10Minutes','controlWardsPlaced','visionScoreAdvantageLaneOpponent'
                    , 'visionScorePerMinute','wardTakedowns','effectiveHealAndShielding','dragonTakedowns','baronTakedowns','teamBaronKills']]
        jungle_col = challenge.filter(regex='^jungle|Jungle|kda')

        match_info = pd.concat([sample , col, jungle_col], axis = 1)
        champion_info = match_info[['participantId','teamId','teamPosition','summonerName','puuid','championName']]
        champion = champion_info['championName']
        teamPosition = champion_info['teamPosition']
        userName = match_info['summonerName']

        df = pd.DataFrame([self.matchId, champion_info['teamId'][0], userName[0], champion[0], teamPosition[0], '세부라인',
                           self.teamFightDamageStats(startPoint, endPoint, '1') 
                      ,self.teamFightReceivedDamageStats(startPoint, endPoint, '1'), self.teamFightCCScores(startPoint, endPoint, '1'), 
                      self.winnerTeamFight(champion_info['teamId'][0], startPoint, endPoint)]).T
        # df = pd.concat([df, pd.DataFrame([self.matchId, champion_info['teamId'][9], userName[9], champion[9], teamPosition[9], '세부라인',
        #                    self.teamFightDamageStats(teamFightPoint, '10') 
        #               ,self.teamFightReceivedDamageStats(teamFightPoint, '10'), self.teamFightCCScores(teamFightPoint, '10'), 
        #               self.winnerTeamFight(champion_info['teamId'][9], teamFightPoint)]).T])
        for i in range(1, 10):
            df = pd.concat([df, pd.DataFrame([self.matchId, champion_info['teamId'][i], userName[i], champion[i], teamPosition[i], '세부라인',
                           self.teamFightDamageStats(startPoint, endPoint, str(i+1)) 
                      ,self.teamFightReceivedDamageStats(startPoint, endPoint, str(i+1)), self.teamFightCCScores(startPoint, endPoint, str(i+1)), 
                      self.winnerTeamFight(champion_info['teamId'][i], startPoint, endPoint)]).T])
        df.columns = ['matchId', 'teamId', 'summonerName', 'champion', 'lane', 'specificLane', 'damage', 
                      'receivedDamage', 'ccScore', 'win/lose']
        # support: 챔피언에게 가한 데미지, 챔피언에게 받은 데미지, CCScore(없는 것: 힐&실드, 딜러에게 가한 비율)
        return df