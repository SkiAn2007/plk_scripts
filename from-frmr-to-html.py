#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# TODO: add check if exist block 'certs'
# version: 3.1

import requests, json, sys, os, datetime
from time import sleep

authGuid = 'secretguid'
folderForResults = 'frmrToHtml'                                             # main directory
folderFofDebugFiles = {'personalJsons': 'personas', 'mainDicts': 'dicts'}   # sub directories
headers = {'Authorization': authGuid, 'Content-Type': 'application/json'}
gdict = {}  # global dict
result_d = {}
idsForDebug = ["11111111111", "00000000000"]  # SNILS numbers
loaddicts = {
	'1.2.643.5.1.13.13.11.1102': 'postid',
	'1.2.643.5.1.13.2.1.1.716': 'specid_of_certs',
	'1.2.643.5.1.13.13.11.1107': 'specid_of_proofs',
	'1.2.643.5.1.13.13.11.1066': 'mpspecid',
	'1.2.643.5.1.13.13.11.1124': 'institutionId',
	'1.2.643.5.1.13.13.11.1110': 'educationTypeId',
	'1.2.643.5.1.13.2.1.1.202': 'qualifyCategoryId',
	'1.2.643.5.1.13.13.11.1100': 'accreditationKindId',
	'1.2.643.5.1.13.13.12.2.78.8646': 'people'
}
problemCases = {'no_profs': [], 'no_certs': [], 'no_accs': [], 'exp_certs': []}
problemCasesDescription = {'no_profs': 'Нет образования', 'no_certs': 'Нет информации о сертификатах',
						   'no_accs': 'Нет интитута в аккредитации', 'exp_certs': 'Все сертификаты просрочены'}

workingDir = sys.path[0] + '/' + folderForResults + '/' + datetime.datetime.now().strftime("%Y.%d.%m") + '/'
for folder in folderFofDebugFiles.values():
	fullFolderPathToCreate = workingDir + folder
	if not os.path.exists(fullFolderPathToCreate):
		os.makedirs(fullFolderPathToCreate)

def loaddict(id, name):
	"""
	Load of the main dictionary and save to file
	"""
	sleep(0.5)
	idd = "urn:oid:%s" % id if name != 'people' else 'urn:oid:1.2.643.2.69.1.1.1.84'
	filePersonDump = workingDir + folderFofDebugFiles['mainDicts'] + '/' + name + '_json.txt'
	requestParameters = {"resourceType": "Parameters", "parameter": [{"name": "system", "valueString": idd}]}
	if name == 'people':
		requestParameters['parameter'].append({"name": "code", "valueString": id})
	jsonRequestParameters = json.dumps(requestParameters)
	with requests.Session() as session:
		operation = 'expand' if name != 'people' else 'lookup'
		url = "http://10.128.66.207:2226/nsi/fhir/term/ValueSet/$%s?_format=json" % operation
		r2 = session.post(url, allow_redirects=True, headers=headers, data=jsonRequestParameters)
	if r2.status_code == 200:
		print('load %s from SITE' % name)
		jsonResponse = r2.json()
		with open(filePersonDump, 'w') as outfile:
			json.dump(jsonResponse, outfile)
	else:
		with open(filePersonDump) as f:
			jsonResponse = json.load(f)
		print('load %s from LOCAL' % name)
	print(r2.status_code, r2.reason)
	return jsonResponse


def getPersonJson(snils):
	sleep(0.5)  # to avoid blocking due to freq.
	url2 = 'http://10.128.66.207:2226/nsi/fhir/term/get_resource'
	payload = {'_format': 'json', 'system': '1.2.643.2.69.1.1.1.104', 'code': snils}
	requestAboutPerson = requests.get(url2, headers=headers, params=payload)
	if requestAboutPerson.status_code == 200:
		data = requestAboutPerson.json()
		if snils in idsForDebug:
			print(requestAboutPerson.text)
		# write response to file
		filename = workingDir + folderFofDebugFiles['personalJsons'] + '/' + snils + '.json'
		with open(filename, 'w') as personalJson:
			json.dump(data, personalJson)
		return data
	else:
		return None
		print(requestAboutPerson.status_code)

def buildPersonCard(data):
	global problemCases
	employee = {}
	print('\r\nProcessing: {0}'.format(data['general']['snils']))
	fio = "{0} {1} {2}".format(data['general'].get('lastName', '-'),
							   data['general'].get('firstName', '-'),
							   data['general'].get('patronymic', '-'))
	print(fio)
	employee['fio'] = fio
	cards_of_medic = []
	if 'cards' in data:
		for card in data['cards']:
			# проверка на не внешнее совместительство 1.2.643.5.1.13.2.1.1.209
			# 1 основное 2 совместительство внутр 3 совмещение 4 совместительство внешнее
			# if card['positionTypeId'] == "1":
			# вдруг внешнее совместительство не в нашем лпу
			# if card['moId'] == "1.2.643.5.1.13.13.12.2.78.8646":
			if card['organizationId'] == "1.2.643.5.1.13.13.12.2.78.8646":
				print(gdict['postid'][card['postId']])
				cards_of_medic.append(gdict['postid'][card['postId']])
	cards_of_medic = list(set(cards_of_medic))
	employee['dolznhost'] = cards_of_medic
	#add accreditation to user
	accs_of_medic = []
	if 'accreditation' in data:
		for acc in data['accreditation']['accreditationProcedures']:
			acc_of_medic = {}
			if 'institutionId' in acc:
				acc_of_medic['institut'] = gdict['institutionId'][acc['institutionId']]
			else:
				acc_of_medic['institut'] = '-'
				problemCases['no_accs'].append(employee['fio'])
			if 'specId' in acc:
				acc_of_medic['spec'] = gdict['specid_of_proofs'][acc['specId']]
			elif 'mpSpecId' in acc:
				acc_of_medic['spec'] = gdict['mpspecid'][acc['mpSpecId']]
			else:
				acc_of_medic['spec'] = ''
				print('-> что-то не так с аккредитацией')
			acc_of_medic['date'] = acc['passDate']
			acc_of_medic['kind'] = gdict['accreditationKindId'][acc['accreditationKindId']]
			accs_of_medic.append(acc_of_medic)
	employee['accs'] = accs_of_medic
	# add certs to user
	certs_of_medic = []
	if 'certs' in data:
		for specc in data['certs']:
			cert_of_medic = {}
			exp_data = datetime.date(*map(int, specc['examDate'].split('-')))
			exp_data2 = exp_data.replace(exp_data.year + 5)
			if (exp_data2 > datetime.date.today()):
				try:
					cert_of_medic['institut'] = gdict['institutionId'][specc['institutionId']]
					# key exists in dict
				except KeyError:
					cert_of_medic['institut'] = 'Не удалось найти запись'
					# key doesn't exist in dict
				cert_of_medic['spec'] = gdict['specid_of_certs'][specc['specId']]
				cert_of_medic['date'] = specc['examDate']
				certs_of_medic.append(cert_of_medic)
		if not certs_of_medic:
			problemCases['exp_certs'].append(employee['fio'])
	else:
		problemCases['no_certs'].append(employee['fio'])
	employee['cert'] = certs_of_medic
	#print certs_of_medic
	if 'profs' in data:
		proofs_of_medic = []
		for proof in data['profs']:
			proof_of_medic = {}
			if proof['educPlace'] == '0':
				if proof['institutionId'] in gdict['institutionId']:
					proof_of_medic['institut'] = gdict['institutionId'][proof['institutionId']]
				else:
					proof_of_medic['institut'] = 'Информация обновляется'
					print('-> Нет института \"%s\" в справочнике' % proof['institutionId'])
				proof_of_medic['spec'] = gdict['specid_of_proofs'][proof['specId']]
				proof_of_medic['edutype'] = gdict['educationTypeId'][proof['educationTypeId']]
				proof_of_medic['date'] = proof['docDate']
			else:
				proof_of_medic['institut'] = proof['foreignInstitution']
				proof_of_medic['spec'] = gdict['specid_of_proofs'][proof['specId']]
				proof_of_medic['edutype'] = gdict['educationTypeId'][proof['educationTypeId']]
				proof_of_medic['date'] = proof['docDate']
			proofs_of_medic.append(proof_of_medic)
		employee['diplom'] = proofs_of_medic
	else:
		print('-> нет образования')
		problemCases['no_profs'].append(employee['fio'])
	qualifs_of_medic = []
	if 'qualifications' in data:
		for qualif in data['qualifications']:
			q_exp_d = datetime.date(*map(int, qualif['beginDate'].split('-')))
			if (q_exp_d > (datetime.date.today()-datetime.timedelta(days=1825))):
				qualif_of_medic = {}
				qualif_of_medic['level'] = gdict['qualifyCategoryId'][qualif['qualifyCategoryId']]
				if 'specId' in qualif:
					qualif_of_medic['spec'] = gdict['specid_of_certs'][qualif['specId']]
				else:
					qualif_of_medic['spec'] = ''
					print('-> Нет specId в квалификации')
					print(qualif)
				qualifs_of_medic.append(qualif_of_medic)
	employee['qualif'] = qualifs_of_medic
	return employee


def buildHtmlTable(resultDict):
	sortedKeys = sorted(resultDict)
	html = "<table class='uk-table uk-table-condensed uk-table-hover speccc1 scroll' cellpadding='0' cellspacing='0'>\r\n<thead><tr><th rowspan='2' >ФИО</th><th rowspan='2' >Должность</th><th>Диплом</th><th>Сертификат или аккредитация (действует 5 лет)</th><th rowspan='2'>Категория</th></tr><tr><th>Тип образования/<br>Учебное заведение/<br>Специальность(Год выдачи)</th><th>Учебное заведение/<br>Специальность(Год выдачи)</th></tr></thead><tbody>\r\n"
	for val in sortedKeys:
			empl = resultDict[val]
			br = '<br />'
			p1 = '<p>'
			p2 = '</p>'
			tr_str = '<tr><td>' + empl['fio'] + '</td>'
			tr_str += "<td>"
			for dol in empl['dolznhost']:
				tr_str += dol + br
			tr_str += '</td><td>'
			if 'diplom' in empl:
				for d in empl['diplom']:
					tr_str += p1 + d['edutype'] + br + d['institut'] + br + d['spec'] + ' (' + d['date'][:4] + ')' + p2
			tr_str += '</td><td>'
			for c in empl['cert']:
				tr_str += p1 + c['institut'] + br + c['spec'] + '(' + c['date'][:4] + ')' + p2
			if 'accs' in empl:
				for ac in empl['accs']:
					tr_str += p1 + ac['kind'] + br + ac['institut'] + br + ac['spec'] + ' (' + ac['date'][:4] + ')' + p2
			tr_str += '</td><td>'
			for q in empl['qualif']:
				tr_str += p1 + q['level'] + br + '(' + q['spec'] + ')' + p2
			tr_str += '</td></tr>\r\n'
			# write string to table if we have info about diplom
			if 'diplom' in empl:
				html += tr_str
	html += '</tbody></table>'
	# write to file
	with open(workingDir + 'result_netrika.html', 'wb') as f:
		f.write(html.encode('utf-8'))

# loading main dicts, parse and save to gdict
for key, value in loaddicts.items():
	gdict[value] = {}
	jsonResponse = loaddict(key, value)
	if value == 'people':
		gdict[value] = jsonResponse
	else:
		for code in jsonResponse['parameter'][0]['resource']['expansion']['contains']:
			gdict[value][code['code']] = code['display']

# get info about all persons
for person in gdict['people']['parameter'][0]['valueCodeableConcept']:
		data = getPersonJson(person['code'])
		if data:
			man = buildPersonCard(data)
			result_d[man['fio']] = man

# make result file
buildHtmlTable(result_d)

# diagnostic prints
print('\r\n====\r\n')
for key, value in problemCasesDescription.items():
	if problemCases[key]:
		print(value, len(problemCases[key]))
		for fio in problemCases[key]:
			print(fio)
		print("\r\n")
# additional check
print('Нет сертификата, но есть диплом:')
no_cert_prof = list(set(problemCases['no_certs']) - set(problemCases['no_profs']))
for name in no_cert_prof:
	print(name)
print('\r\n')

print('FINISH!')
