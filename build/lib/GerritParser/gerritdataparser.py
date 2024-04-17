# -*- coding: UTF-8 -*-
import hashlib
import json
import re


class GerritDataParser:
    def __init__(self, fn_config, ruleset=None):
        print('Instantiate %s' % self.__class__.__name__)
        self.__fn_config = fn_config
        with open(fn_config, mode='r') as f:
            parse_config = json.load(f)
        list_ruleset = parse_config['repoProfiles'].keys()
        assert (ruleset is None) or (ruleset in list_ruleset), 'Unsupported ruleset %s' % ruleset
        self.__ruleset = ruleset
        self.__troubleshooting = (ruleset is None)
        self.__finding_categories = parse_config['findingCategory']
        self.__remove_cmtduplication = parse_config['removeCommentDuplication']
        self.__repo_patterns = self.__get_repopattern(parse_config)
        self.__status_wlist = parse_config['repoProfiles'][ruleset]['Status_Whitelist'] if ruleset else None
        self.__patch_blist = parse_config['repoProfiles'][ruleset]['Patchset_Kind_Blacklist'] if ruleset else None
        self.__fkind_rules = parse_config['repoProfiles'][ruleset]['Kind_Rules'] if ruleset else None
        self.__tech_rules = parse_config['repoProfiles'][ruleset]['Tech_Rules'] if ruleset else None
        self.__path_blist = parse_config['repoProfiles'][ruleset]['Path_Blacklist'] if ruleset else None
        self.__fchange_types_blist = (
            parse_config)['repoProfiles'][ruleset]['File_Change_Type_Blacklist'] if ruleset else None
        self.__reviewer_blist = (
            parse_config)['repoProfiles'][ruleset]['Reviewer_Username_Blacklist'] if ruleset else None
        self.__author_blist = parse_config['repoProfiles'][ruleset]['Author_Username_Blacklist'] if ruleset else None

        if self.__ruleset:
            print('%s code repository is configured' % self.__ruleset)
        else:
            print('No code repository is configured yet. '
                  'Please call evaluate_ruleset(record) with Gerrit response sample to complete the configuration '
                  'before the other operation')

    def __del__(self):
        print('Destroy %s' % self.__class__.__name__)

    @property
    def ruleset(self):
        return self.__ruleset

    @staticmethod
    def __get_repopattern(parse_config):
        list_repopattern = []
        for rsetname, rsetvalue in parse_config['repoProfiles'].items():
            repopatts = rsetvalue['Project_Pattern_RegEx']
            list_repopattern.append({rsetname: repopatts})
        return list_repopattern

    def evaluate_ruleset(self, record):
        assert record and 'project' in record.keys(), 'Illegal Gerrit response data'

        project = record['project']

        ruleset = None
        for repopatt in self.__repo_patterns:
            for rsetname, rsetvalue in repopatt.items():
                for patt in repopatt[rsetname]:
                    m_proj = re.match(r'%s' % patt, project)
                    if m_proj:
                        ruleset = rsetname
                        break
                if ruleset:
                    break
            if ruleset:
                break
        print('Gerrit project \"%s\" is mapped to ruleset \"%s\"' % (project, ruleset))

        if ruleset:
            self.config_ruleset(ruleset)
        return ruleset

    def config_ruleset(self, ruleset):
        self.__ruleset = ruleset
        with open(self.__fn_config, mode='r') as f:
            parse_config = json.load(f)
        self.__finding_categories = parse_config['findingCategory']
        self.__repo_patterns = self.__get_repopattern(parse_config)
        self.__status_wlist = parse_config['repoProfiles'][ruleset]['Status_Whitelist']
        self.__patch_blist = parse_config['repoProfiles'][ruleset]['Patchset_Kind_Blacklist']
        self.__fkind_rules = parse_config['repoProfiles'][ruleset]['Kind_Rules']
        self.__tech_rules = parse_config['repoProfiles'][ruleset]['Tech_Rules']
        self.__path_blist = parse_config['repoProfiles'][ruleset]['Path_Blacklist']
        self.__fchange_types_blist = parse_config['repoProfiles'][ruleset]['File_Change_Type_Blacklist']
        self.__reviewer_blist = parse_config['repoProfiles'][ruleset]['Reviewer_Username_Blacklist']
        self.__author_blist = parse_config['repoProfiles'][ruleset]['Author_Username_Blacklist']
        print('%s code repository is configured' % ruleset)

    # def __ruleset(self, rec):
    #     if self.__ruleset is None:
    #         self.__ruleset = self.evaluate_ruleset(rec)
    #     return self.__ruleset

    def __read_profile_from_record(self, record):
        """
        Extract review profile from a review record.
        :param record: A set of Gerrit data for a single review ID from Gerrit server.
        :return:
        """
        cmessage = record[
            'commitMessage']  # .encode('latin1').decode('unicode-escape').encode('latin1').decode('utf-8')

        featureList = []
        if self.__ruleset == "5GUP":
            m_strFeatures = re.match(r"\[(.*)?\].*", cmessage)
            if m_strFeatures:
                strFeatures = m_strFeatures.group(1)
                list_feature = strFeatures.split(',')
                for feature in list_feature:
                    m_featureId = re.match(r'^([a-zA-Z0-9-]+)', feature, re.I)
                    if m_featureId and m_featureId.group(1).upper() != 'NONE':
                        featureList.append(m_featureId.group(1))
        elif self.__ruleset == "Tdd":
            m_strFeatures = re.match(r'^FEATURE:(NF|PR|IN) +([\S\-,]+|) .*', cmessage)
            if m_strFeatures:
                strFeatures = m_strFeatures.group(2) if m_strFeatures.group(1) in ['NF', 'PR'] else ''
                list_feature = strFeatures.split(',')
                for feature in list_feature:
                    m_featureId = re.match(r'^([a-zA-Z0-9-]+)', feature, re.I)
                    if m_featureId:
                        featureList.append(m_featureId.group(1))
        else:
            featureList = []

        # if 'NONE' in featureList:
        #     featureList.remove('NONE')

        tagList = []
        m_strIdTag = re.findall(r'%(JID|PR|NF|INT_SW_CHANGE) *= *(\S+)', cmessage, re.M)
        if m_strIdTag:
            list_idtag = [strIdTag[1].strip() for strIdTag in m_strIdTag]
            for idtag in list_idtag:
                m_idtag = re.match(r'^([a-zA-Z0-9-]+)', idtag, re.I)
                if m_idtag:
                    tagList.append(m_idtag.group(1).upper())

        rprofile = {'project': record['project'], 'branch': record['branch'], 'createdOn': record['createdOn'],
                    'id': record['id'], 'reviewId': record['number'],
                    'subject': record['subject'], 'featureId': featureList, 'idTag': tagList,
                    'owner': record['owner'], 'status': record['status'], 'lastUpdated': record['lastUpdated']}
        return rprofile

    def __get_fileproperties(self, file: str):
        # print('Parse file %s' % file, flush=True)
        filekind = None
        for reitem in self.__fkind_rules:
            matched = False
            m_filekind = re.match(r'%s' % reitem['Regex'], file)
            if m_filekind:
                matched = True
                # toexclude = False
                if reitem['Exclude']:
                    for exitem in reitem['Exclude']:
                        m_fileexcl = re.match(r'%s' % exitem, file)
                        if m_fileexcl:
                            matched = False
                            # toexclude = True
                            break
                # if toexclude:
                #     continue
            if matched:
                filekind = reitem['Kind']
                break
            else:
                continue
        if filekind is None:
            filekind = 'Undef'

        tech = None
        for reitem in self.__tech_rules:
            matched = False
            m_filetech = re.match(r'%s' % reitem['Regex'], file)
            if m_filetech:
                matched = True
                # toexclude = False
                if reitem['Exclude']:
                    for exitem in reitem['Exclude']:
                        m_fileexcl = re.match(r'%s' % exitem, file)
                        if m_fileexcl:
                            matched = False
                            # toexclude = True
                            break
                # if toexclude:
                #     continue
            if matched:
                tech = reitem['Tech']
                break
            else:
                continue
        if tech is None:
            tech = 'Unknown'

        fileProperties = {'file': file, 'fileKind': filekind, 'tech': tech}
        return fileProperties

    def get_fileproperties(self, file: str):
        return self.__get_fileproperties(file)

    def __category_finding(self, message: str) -> str:
        category = None
        m_category = re.match(r'\[(\S+?)\]\s*\S+', message)
        if m_category:
            category = m_category.group(1)
            found = False
            for c in self.__finding_categories:
                if c.upper() == category.upper():
                    category = c
                    found = True
                    break
            if not found:
                category = None
        return category

    @staticmethod
    def __comment_hashid(file: str, line: int, username: str, message: str) -> str:
        hashinstance = hashlib.md5('comment'.encode('utf-8'))
        hashinstance.update(('\"%s\" by %s @ %s:%d' % (message, username, file, line)).encode('utf-8'))
        return hashinstance.hexdigest()

    def __read_from_patchsets(self, record: dict) -> dict:
        """
        Extract properties of files & comments from "patchSets" of Gerrit response.
        :param record: A set of Gerrit data for a single review ID from Gerrit server. Mandatory to include
        "patchSets" field.
        :return: {'totalInsertions': total_insertions, 'totalDeletions': total_deletions,
                'patchList': patchlist, 'fileList': fileList}
        """
        if 'patchSets' not in record.keys():
            print('Error: Key \"patchSets\" is not found. '
                  'Please check whether option --patchsets is used in Gerrit query command.')
            return None

        fileList = []
        patchlist = []
        total_insertions, total_deletions = 0, 0
        patchsets = record['patchSets']
        for patchset in patchsets:
            if patchset['kind'] in self.__patch_blist:
                if self.__troubleshooting:
                    print('Info: Patchset %d is ignored because its kind (%s) is in blacklist' %
                          (patchset['number'], patchset['kind']))
                continue

            patchdata = {'patchsetNo': patchset['number']}
            if 'files' not in patchset.keys():
                print('Error: Key \"files\" is not found. '
                      'Please check whether option --files is used in Gerrit query command.')
                continue

            patchfileList = []
            sum_insertions, sum_deletions = 0, 0
            files = patchset['files']
            for file in files:
                if file['type'] in self.__fchange_types_blist:
                    if self.__troubleshooting:
                        print('Info: File %s is ignored because its change type (%s) is in blacklist' %
                              (file['file'], file['type']))
                    continue

                path_in_blist = False
                for pbregex in self.__path_blist:
                    match_path_blist = re.match(r'%s' % pbregex, file['file'])
                    if match_path_blist:
                        path_in_blist = True
                        break
                if path_in_blist:
                    if self.__troubleshooting:
                        print('Info: File %s is ignored because its path is in blacklist' % file['file'])
                    continue

                # print('Attempt to parse %s' % file['file'], flush=True)
                fileProperties = self.__get_fileproperties(file['file'])
                fileProperties.update({'type': file['type'],
                                       'insertions': file['insertions'], 'deletions': file['deletions']})
                fileProfile = {'patchSet': patchset['number']}
                fileProfile.update(fileProperties)
                patchfileList.append(fileProfile)
                fileList.append(fileProfile)

                sum_insertions += file['insertions']
                sum_deletions += file['deletions']

            patchdata.update({'patchset_kind': patchset['kind'],
                              'insertions': sum_insertions, 'deletions': sum_deletions, 'fileList': patchfileList})

            findingList = []
            [fileset.update({'authorCommentNum': int(0)}) for fileset in patchfileList]
            [fileset.update({'wlistCommentNum': int(0)}) for fileset in patchfileList]
            [fileset.update({'blistCommentNum': int(0)}) for fileset in patchfileList]
            if 'comments' in patchset.keys():
                comments = patchset['comments']

                # Remove comment duplication
                if self.__remove_cmtduplication:
                    prev_comment_hid = None
                    list_comment = []
                    for comment in comments:
                        curr_comment_hid = self.__comment_hashid(comment['file'], comment['line'],
                                                                 comment['reviewer']['username'],
                                                                 comment['message'])
                        if curr_comment_hid == prev_comment_hid:
                            print('Warning: Remove duplicated comment: '
                                  '\"%s\" by %s @ %s:%d' % (comment['message'],
                                                            comment['reviewer']['username'],
                                                            comment['file'],
                                                            comment['line']))
                        else:
                            prev_comment_hid = curr_comment_hid
                            list_comment.append(comment)
                else:
                    list_comment = comments

                for comment in list_comment:
                    # if comment['reviewer']['username'] in self.__reviewer_blist:
                    #     continue

                    # Map comment number to each file
                    found = False
                    for file_cache in patchfileList:
                        if file_cache['file'] == comment['file']:
                            found = True
                            if comment['reviewer']['username'] in self.__reviewer_blist:
                                file_cache['blistCommentNum'] += 1
                            else:
                                file_cache['wlistCommentNum'] += 1
                            if comment['reviewer']['username'] == record['owner']['username']:
                                file_cache['authorCommentNum'] += 1
                            break
                    if not found:
                        if self.__troubleshooting:
                            print('Warning: File %s has comments but is not finally submitted.' % comment['file'])
                        # continue

                    if 'message' in comment.keys():
                        category = self.__category_finding(comment['message'])
                    else:
                        category = None
                    finding_temp = {'file': comment['file'], 'line': comment['line'], 'category': category}

                    # if comment['line'] == 38:
                    #     print('I am checking %s:%s' % (comment['file'], comment['line']))

                    # Map comment number to each finding
                    fileProperties = self.__get_fileproperties(comment['file'])
                    finding_temp.update({'fileKind': fileProperties['fileKind']})
                    found = False
                    for finding_cache in findingList:
                        if (finding_cache['file'] == finding_temp['file']) and \
                                (finding_cache['line'] == finding_temp['line']):
                            found = True

                            # Keep finding category
                            if category:
                                finding_cache.update({'category': category})

                            # Count comments
                            if comment['reviewer']['username'] in self.__reviewer_blist:
                                finding_cache['blistCommentNum'] += 1
                            else:
                                finding_cache['wlistCommentNum'] += 1
                            if comment['reviewer']['username'] == record['owner']['username']:
                                finding_cache['authorCommentNum'] += 1

                            # Keep reviewers (not including author)
                            if ((comment['reviewer']['username'] != record['owner']['username']) and
                                    (comment['reviewer']['username'] not in finding_cache['reviewer_usernames']) and
                                    (comment['reviewer']['username'] not in self.__reviewer_blist)):
                                finding_cache['reviewers'].append(comment['reviewer'])
                                finding_cache['reviewer_usernames'].append(comment['reviewer']['username'])
                            break
                    if not found:
                        if comment['reviewer']['username'] == record['owner']['username']:
                            finding_temp.update({'authorCommentNum': int(1),
                                                 'reviewers': [],
                                                 'reviewer_usernames': []})
                        elif comment['reviewer']['username'] in self.__reviewer_blist:
                            finding_temp.update({'authorCommentNum': int(0),
                                                 'reviewers': [],
                                                 'reviewer_usernames': []})
                        else:
                            finding_temp.update({'authorCommentNum': int(0),
                                                 'reviewers': [comment['reviewer']],
                                                 'reviewer_usernames': [comment['reviewer']['username']]})
                        if comment['reviewer']['username'] in self.__reviewer_blist:
                            finding_temp.update({'wlistCommentNum': int(0), 'blistCommentNum': int(1)})
                        else:
                            finding_temp.update({'wlistCommentNum': int(1), 'blistCommentNum': int(0)})

                        # # In case of no eligible reviewer, not keep the finding
                        # if len(finding_temp['reviewers']) > 0:
                        #     findingList.append(finding_temp)
                        findingList.append(finding_temp)

            # Key reviewer_usernames is used to distinct reviewers. It is intermediate and ultimately removed.
            [finding.pop('reviewer_usernames') for finding in findingList]

            # In case of no whitelist reviewer, do not keep the finding
            for finding in findingList:
                if finding['wlistCommentNum'] == 0:
                    findingList.remove(finding)

            if record['owner']['username'] in self.__reviewer_blist:
                patchdata.update({'findingList': findingList})
            else:
                patchdata.update({'findingList': findingList})
            patchlist.append(patchdata)

            total_insertions += sum_insertions
            total_deletions += sum_deletions

        return {'totalInsertions': total_insertions, 'totalDeletions': total_deletions,
                'patchList': patchlist, 'fileList': fileList}

    @staticmethod
    def __is_commentedby_gerrit(message: str) -> bool:
        return re.match(r'^Patch Set \d+: Code-Review[+-]\d.*', message, re.M) is not None

    def __read_from_comments(self, record: dict) -> dict:
        """
        Extract overall review profile from "comments" field of Gerrit response.
        :param record: A set of Gerrit data for a single review ID from Gerrit server. Mandatory to include
        "comments" field.
        :return: {'totalComments': num_comments, 'commentList': list_comment}
        """
        if 'comments' not in record.keys():
            return None

        num_comments = 0
        first_submitted = None
        approver = None
        lastup_patchno = None
        list_comment = []
        commentsets = record['comments']
        for commentset in commentsets:
            # Check each comment for final +2 operation. There is the case of multiple +2 in a review session. This
            # depends on the assumption that all comments are order ascending in time.
            # if first_submitted is None: # This if statement is commented because of above reason.
            # m_patchno = re.match(r'^Uploaded patch set (\d+)', commentset['message'])
            # if m_patchno:
            #     lastup_patchno = m_patchno.group(1)
            # m_submitted = re.match(r'.* submitted as [a-z0-9]+ .*', commentset['message'])
            m_submitted = re.match(r'.* (\d+): Code-Review\+2', commentset['message'])
            if m_submitted:
                lastup_patchno = m_submitted.group(1)
                first_submitted = commentset['timestamp']
                approver = commentset['reviewer']

            if 'username' not in commentset['reviewer'].keys():
                # print('\nWarning: Key \"username\" is missing for comment \"%s\"', commentset['message'])
                continue

            assert 'username' in commentset['reviewer'].keys(), 'Key \"username\" missing from %s.\n%s' % (
                record['number'], json.dumps(commentset))
            if commentset['reviewer']['username'] in self.__reviewer_blist:
                commentedBy = 'blacklistReviewer'
            elif commentset['reviewer']['username'] == record['owner']['username']:
                commentedBy = 'reviewOwner'
            elif self.__is_commentedby_gerrit(commentset['message']):
                commentedBy = 'Gerrit'
            else:
                commentedBy = 'eligibleReviewer'

            num_comments += 1
            list_comment.append({'reviewer': commentset['reviewer'],
                                 'message': commentset['message'],
                                 'commentedBy': commentedBy})

        return {'totalComments': num_comments, 'commentList': list_comment,
                'first_submitted': first_submitted, 'approver': approver,
                'lastUploaded_PatchNo': int(lastup_patchno) if lastup_patchno else 0}

    @staticmethod
    def __summrize_finalchange(profile):
        if profile['lastUploaded_PatchNo'] is None:
            assert True, 'Final patch not identified'
            return []
        list_finalchange = []
        lastup_patno = profile['lastUploaded_PatchNo']
        for fileSet in profile['fileList']:
            if lastup_patno == fileSet['patchSet']:
                list_finalchange.append(fileSet)
        return list_finalchange

    def __summrize_codereview(self, profile):
        dict_attrbyfilekind = {}
        for patch in profile['patchList']:
            for fileProfile in patch['fileList']:
                if fileProfile['fileKind'] in dict_attrbyfilekind.keys():
                    wlistCommentNum = dict_attrbyfilekind[fileProfile['fileKind']]['wlistCommentNum']
                    authorCommentNum = dict_attrbyfilekind[fileProfile['fileKind']]['authorCommentNum']
                    blistCommentNum = dict_attrbyfilekind[fileProfile['fileKind']]['blistCommentNum']
                    dict_attrbyfilekind[fileProfile['fileKind']].update(
                        {
                            'wlistCommentNum': wlistCommentNum + fileProfile['wlistCommentNum'],
                            'authorCommentNum': authorCommentNum + fileProfile['authorCommentNum'],
                            'blistCommentNum': blistCommentNum + fileProfile['blistCommentNum']
                        }
                    )
                else:
                    dict_attrbyfilekind.update(
                        {
                            fileProfile['fileKind']: {
                                'wlistCommentNum': fileProfile['wlistCommentNum'],
                                'authorCommentNum': fileProfile['authorCommentNum'],
                                'blistCommentNum': fileProfile['blistCommentNum'],
                                'insertions': 0,
                                'deletions': 0
                            }
                        }
                    )

        list_finalchange = self.__summrize_finalchange(profile)
        for filechange in list_finalchange:
            if filechange['fileKind'] in dict_attrbyfilekind.keys():
                insertions = dict_attrbyfilekind[filechange['fileKind']]['insertions']
                deletions = dict_attrbyfilekind[filechange['fileKind']]['deletions']
                dict_attrbyfilekind[filechange['fileKind']].update(
                    {
                        'insertions': insertions + filechange['insertions'],
                        'deletions': deletions + filechange['deletions']
                    }
                )
            else:
                dict_attrbyfilekind.update(
                    {
                        filechange['fileKind']: {
                            'wlistCommentNum': 0,
                            'authorCommentNum': 0,
                            'blistCommentNum': 0,
                            'insertions': filechange['insertions'],
                            'deletions': filechange['deletions']
                        }
                    }
                )

        return dict_attrbyfilekind

    def get_findings(self, record: dict) -> list:
        dict_codechanges = self.__read_from_patchsets(record)
        list_filechange = dict_codechanges['fileList']
        return list_filechange

    def parse_record(self, rec: dict) -> dict:
        """
        Parse code review payload from Gerrit server
        :param rec: Code review payload specific for single review ticket/ID.
        :return: A dictionary including key information of this review ticket. A dictionary including key "failure"
        is returned in case hitting configured blacklist.
        """
        assert 'status' in rec.keys(), 'Key status missing:\n%s' % json.dumps(rec, indent=4)
        if rec['status'] not in self.__status_wlist:
            return {'reviewId': rec['number'], 'failure': 'Ignore status \"%s\"' % rec['status']}
        elif rec['owner']['username'] in self.__author_blist:
            return {'reviewId': rec['number'], 'failure': 'Ignore author \"%s\"' % rec['owner']['name']}

        data = {'reviewId': rec['number'],
                'profile': self.__read_profile_from_record(rec)}
        data['profile'].update(self.__read_from_comments(rec))
        data['profile'].update(self.__read_from_patchsets(rec))
        # list_finalchange = self.__summrize_finalchange(data['profile'])
        # data.update({'submittedChange': list_finalchange})
        dict_summary = self.__summrize_codereview(data['profile'])
        data.update({'summary': dict_summary})
        return data
