from SDLParser import *
from config import *
from transform import *
from rcca import *
import sys

SDLLinesForKeygen = []

def getIsVarList(keygenOutputElem, keygenOutputVarInfo, assignInfo, varTypes):
    if ( (keygenOutputVarInfo.getIsList() == True) or (len(keygenOutputVarInfo.getListNodesList()) > 0) ):
        return True

    try:
        currentVarType = varTypes[TYPES_HEADER][keygenOutputElem].getType()
    except:
        return False

    if ( (currentVarType == types.list) or (currentVarType == ops.LIST) ):
        return True

    return False

def removeListIndices(inputString):
    inputStringSplit = inputString.split(LIST_INDEX_SYMBOL)
    return inputStringSplit[0]

def removeListIndicesAndDupsFromList(inputList):
    retList = []

    for inputListEntry in inputList:
        entryWithoutIndices = removeListIndices(inputListEntry)
        if (entryWithoutIndices not in retList):
            retList.append(entryWithoutIndices)

    return retList

def writeForAllLoop(keygenOutputElem, varsToBlindList, varNamesForListDecls):
    global SDLLinesForKeygen

    SDLLinesForKeygen.append("BEGIN :: forall\n")
    SDLLinesForKeygen.append("forall{" + blindingLoopVar + " := " + keygenOutputElem + "}\n")
    SDLLinesForKeygen.append(keygenOutputElem + blindingSuffix + LIST_INDEX_SYMBOL + blindingLoopVar + " := " + keygenOutputElem + LIST_INDEX_SYMBOL + blindingLoopVar + " ^ (1/" + keygenBlindingExponent + ")\n")
    SDLLinesForKeygen.append("END :: forall\n")
    varsToBlindList.remove(keygenOutputElem)
    if (keygenOutputElem in varNamesForListDecls):
        sys.exit("writeForAllLoop in keygen.py attempted to add duplicate keygenOutputElem to varNamesForListDecls -- 2 of 2.")
    varNamesForListDecls.append(keygenOutputElem)

def varListContainsParentDict(varList, parentDict):
    for varName in varList:
        varNameWithoutIndices = removeListIndices(varName)
        if (varNameWithoutIndices == parentDict):
            return True

    return False

def blindKeygenOutputElement(keygenOutputElem, varsToBlindList, varNamesForListDecls):
    global SDLLinesForKeygen

    assignInfo = getAssignInfo()
    varTypes = getVarTypes()

    varsModifiedInKeygen = list(assignInfo[keygenFuncName].keys())
    varsModifiedInKeygen = removeListIndicesAndDupsFromList(varsModifiedInKeygen)

    if (keygenOutputElem not in varsModifiedInKeygen):
        SDLLinesForKeygen.append(keygenOutputElem + blindingSuffix + " := " + keygenOutputElem + "\n")
        varsToBlindList.remove(keygenOutputElem)
        return keygenOutputElem

    if (keygenOutputElem not in assignInfo[keygenFuncName]):
        if (varListContainsParentDict(assignInfo[keygenFuncName].keys(), keygenOutputElem) == False):
            sys.exit("keygen output element passed to blindKeygenOutputElement in keygen.py is not in assignInfo[keygenFuncName], and is not a parent dictionary of one of the variables in assignInfo[keygenFuncName].")
        writeForAllLoop(keygenOutputElem, varsToBlindList, varNamesForListDecls)
        return keygenOutputElem

    keygenOutputVarInfo = assignInfo[keygenFuncName][keygenOutputElem]

    isVarList = getIsVarList(keygenOutputElem, keygenOutputVarInfo, assignInfo, varTypes)

    if (isVarList == False):
        SDLLinesForKeygen.append(keygenOutputElem + blindingSuffix + " := " + keygenOutputElem + " ^ (1/" + keygenBlindingExponent + ")\n")
        varsToBlindList.remove(keygenOutputElem)
        return keygenOutputElem

    if ( (keygenOutputVarInfo.getIsList() == True) and (len(keygenOutputVarInfo.getListNodesList()) > 0) ):
        listMembers = keygenOutputVarInfo.getListNodesList()
        listMembersString = ""
        for listMember in listMembers:
            listMembersString += listMember + blindingSuffix + ", "
            blindKeygenOutputElement(listMember, varsToBlindList, varNamesForListDecls)
        listMembersString = listMembersString[0:(len(listMembersString)-2)]
        SDLLinesForKeygen.append(keygenOutputElem + blindingSuffix + " := list{" + listMembersString + "}\n")
        #varsToBlindList.remove(keygenOutputElem)
        if (keygenOutputElem in varNamesForListDecls):
            sys.exit("blindKeygenOutputElement in keygen.py attempted to add duplicate keygenOutputElem to varNamesForListDecls -- 1 of 2.")
        #varNamesForListDecls.append(keygenOutputElem)
        return keygenOutputElem

    writeForAllLoop(keygenOutputElem, varsToBlindList, varNamesForListDecls)
    return keygenOutputElem

def keygen(file):
    global SDLLinesForKeygen

    if ( (type(file) is not str) or (len(file) == 0) ):
        sys.exit("First argument passed to keygen.py is invalid.")

    parseFile2(file, False)
    (varsToBlindList, rccaData) = (transform(False))
    rcca(rccaData)
    varNamesForListDecls = []

    assignInfo = getAssignInfo()

    if (keygenBlindingExponent in assignInfo[keygenFuncName]):
        sys.exit("keygen.py:  the variable used for keygenBlindingExponent in config.py already exists in the keygen function of the scheme being analyzed.")

    if ( (keygenFuncName not in assignInfo) or (outputKeyword not in assignInfo[keygenFuncName]) ):
        sys.exit("assignInfo structure obtained in keygen function of keygen.py did not have the right keygen function name or output keywords.")

    keygenOutput = assignInfo[keygenFuncName][outputKeyword].getVarDeps()
    if (len(keygenOutput) == 0):
        sys.exit("Variable dependencies obtained for output of keygen in keygen.py was of length zero.")

    SDLLinesForKeygen.append(keygenBlindingExponent + " := random(ZR)\n")

    for keygenOutput_ind in keygenOutput:
        secretKeyName = blindKeygenOutputElement(keygenOutput_ind, varsToBlindList, varNamesForListDecls)

    SDLLinesForKeygen.append("output := list{" + keygenBlindingExponent + ", " + secretKeyName + blindingSuffix + "}\n")

    if (len(varsToBlindList) != 0):
        sys.exit("keygen.py completed without blinding all of the variables passed to it by transform.py.")

    lineNoKeygenOutput = getLineNoOfOutputStatement(keygenFuncName)
    removeFromLinesOfCode([lineNoKeygenOutput])
    appendToLinesOfCode(SDLLinesForKeygen, lineNoKeygenOutput)

    for index_listVars in range(0, len(varNamesForListDecls)):
        varNamesForListDecls[index_listVars] = varNamesForListDecls[index_listVars] + blindingSuffix + " := list\n"

    lineNoEndTypesSection = getEndLineNoOfFunc(TYPES_HEADER)
    appendToLinesOfCode(varNamesForListDecls, lineNoEndTypesSection)

    parseLinesOfCode(getLinesOfCode(), False)

if __name__ == "__main__":
    keygen(sys.argv[1])
    printLinesOfCode()
