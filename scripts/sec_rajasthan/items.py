# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
import json
from collections import OrderedDict
import six


class OrderedItem(scrapy.Item):
    def __init__(self, *args, **kwargs):
        self._values = OrderedDict()
        if args or kwargs:
            for k, v in six.iteritems(dict(*args, **kwargs)):
                self[k] = v

    def __repr__(self):
        return json.dumps(OrderedDict(self),ensure_ascii = False)
        #ensure_ascii = False ,it make characters show in cjk appearance.


class ContestingSarpanchItem(OrderedItem):
    fields_to_export = ['ElectionType', 'ElectionDuration', 'District', 'PanchayatSamiti',
                        'SrNo', 'NameOfGramPanchayat', 'CategoryOfGramPanchayat',
                        'ContestingCandidateSerialNo', 'NameOfContestingCandidate',
                        'FatherHusbandOfContestingCandidate', 'Gender', 'MartialStatus',
                        'CategoryOfCandidate', 'EducationStatus',
                        'ContestingCandidateOccupation', 'Age',
                        'TotalValueOfCapitalAssets',
                        'ChildrenBefore27111995', 'ChildrenOnOrAfter28111995', 'MobileNo', 'EmailAddress']
    ElectionType = scrapy.Field()
    ElectionDuration = scrapy.Field()
    District = scrapy.Field()
    PanchayatSamiti = scrapy.Field()
    SrNo = scrapy.Field()
    NameOfGramPanchayat = scrapy.Field()
    CategoryOfGramPanchayat = scrapy.Field()
    ContestingCandidateSerialNo = scrapy.Field()
    NameOfContestingCandidate = scrapy.Field()
    FatherHusbandOfContestingCandidate = scrapy.Field()
    Gender = scrapy.Field()
    MartialStatus = scrapy.Field()
    CategoryOfCandidate = scrapy.Field()
    EducationStatus = scrapy.Field()
    ContestingCandidateOccupation = scrapy.Field()
    Age = scrapy.Field()
    TotalValueOfCapitalAssets = scrapy.Field()
    ChildrenBefore27111995 = scrapy.Field()
    ChildrenOnOrAfter28111995 = scrapy.Field()
    MobileNo = scrapy.Field()
    EmailAddress = scrapy.Field()


class StatsNominationItem(OrderedItem):
    fields_to_export = ['ElectionType', 'ElectionDuration', 'District', 'PanchayatSamiti',
                        'SrNo', 'GramPanchayat', 'NominationTotalNoOfNominationFilled',
                        'NominationCandidate', 'ValidlyNominatedCandidate',
                        'Withdrawal', 'Unopposed', 'Contestants']
    ElectionType = scrapy.Field()
    ElectionDuration = scrapy.Field()
    District = scrapy.Field()
    PanchayatSamiti = scrapy.Field()
    SrNo = scrapy.Field()
    GramPanchayat = scrapy.Field()
    NominationTotalNoOfNominationFilled = scrapy.Field()
    NominationCandidate = scrapy.Field()
    ValidlyNominatedCandidate = scrapy.Field()
    Withdrawal = scrapy.Field()
    Unopposed = scrapy.Field()
    Contestants = scrapy.Field()


class WinnerSarpanchItem(OrderedItem):
    fields_to_export = ['ElectionType', 'ElectionDuration', 'District', 'PanchayatSamiti',
                        'SrNo', 'NameOfGramPanchyat', 'CategoryOfGramPanchyat',
                        'TotalNoOfContestingCandidate', 'ElectedUnoppose',
                        'TotalElectorateVotes', 'TotalPolledVotes', 'RejectedVotes',
                        'TotalValidVotes', 'PollPercent', 'WinnerCandidateName', 'ViewPledge',
                        'VoteSecureByWinner', 'RunnerupCandidateName', 'VoteSecureByRunnerup',
                        'TotalNoOfNOTACount', 'TenderedVotes']
    ElectionType = scrapy.Field()
    ElectionDuration = scrapy.Field()
    District = scrapy.Field()
    PanchayatSamiti = scrapy.Field()
    SrNo = scrapy.Field()
    NameOfGramPanchyat = scrapy.Field()
    CategoryOfGramPanchyat = scrapy.Field()
    TotalNoOfContestingCandidate = scrapy.Field()
    ElectedUnoppose = scrapy.Field()
    TotalElectorateVotes = scrapy.Field()
    TotalPolledVotes = scrapy.Field()
    RejectedVotes = scrapy.Field()
    TotalValidVotes = scrapy.Field()
    PollPercent = scrapy.Field()
    WinnerCandidateName = scrapy.Field()
    ViewPledge = scrapy.Field()
    VoteSecureByWinner = scrapy.Field()
    RunnerupCandidateName = scrapy.Field()
    VoteSecureByRunnerup = scrapy.Field()
    TotalNoOfNOTACount = scrapy.Field()
    TenderedVotes = scrapy.Field()


class WarnWinningPanchItem(OrderedItem):
    fields_to_export = ['ElectionType', 'ElectionDuration', 'District', 'PanchayatSamiti',
                        'SrNo', 'Grampanchayat', 'WardNo', 'NameOfVillage',
                        'CategoryOfWard', 'NameOfCandidate', 'TotalNoOfVotes',
                        'VotesPolled', 'PollPercent', 'WhetherElectedUnoppose',
                        'CategoryOfWinningCandidate', 'RemarkIfAny', 'WinnerVotes',
                        'LooserVotes']
    ElectionType = scrapy.Field()
    ElectionDuration = scrapy.Field()
    District = scrapy.Field()
    PanchayatSamiti = scrapy.Field()
    SrNo = scrapy.Field()
    Grampanchayat = scrapy.Field()
    WardNo = scrapy.Field()
    NameOfVillage = scrapy.Field()
    CategoryOfWard = scrapy.Field()
    NameOfCandidate = scrapy.Field()
    TotalNoOfVotes = scrapy.Field()
    VotesPolled = scrapy.Field()
    PollPercent = scrapy.Field()
    WhetherElectedUnoppose = scrapy.Field()
    CategoryOfWinningCandidate = scrapy.Field()
    RemarkIfAny = scrapy.Field()
    WinnerVotes = scrapy.Field()
    LooserVotes = scrapy.Field()
