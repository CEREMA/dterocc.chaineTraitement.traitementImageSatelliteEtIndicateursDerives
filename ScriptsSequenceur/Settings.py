#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# STRUCTURE QUI DEFINIT LES PARAMETRES NECESSAIRES A LA CHAINE DE TRAITEMENTS                                                               #
#                                                                                                                                           #
#############################################################################################################################################

# Définition des constantes
TAG_ACTION_TO_MAKE_NOW = "Immediat"
TAG_ACTION_TO_MAKE_BG  = "Background"
TAG_ACTION_TO_MAKE_RE  = "Remote"

TAG_STATE_MAKE  = "A_Faire"
TAG_STATE_WAIT  = "En_Attente"
TAG_STATE_LOCK  = "Bloque"
TAG_STATE_RUN   = "En_Cours"
TAG_STATE_END   = "Termine"
TAG_STATE_ERROR = "En_Erreur"

FUNCTION_PYTHON = "python -m "
FUNCTION_PYTHON3 = "python3 -m "
STOP_SERVEUR = "Stop"
SEPARATOR = " # "

IP_VERSION = "IPv4"

# Variable globale : isEndDisplay : boolean indiquant la fin du calcul du graphe et de son affichage
isEndDisplay = False
def setEndDisplay(boolValue):
    global isEndDisplay
    isEndDisplay = boolValue

def getEndDisplay():
    global isEndDisplay
    return isEndDisplay

# Données Generales
class StructTask:
    def __init__(self):
        self.taskLabel = ''
        self.dependencyTaskList = []
        self.taskIdTaskCommandsList = []
        self.typeExecution = ''
        self.position = 0
        self.errorManagement = True
        self.settings = ''

class StructRemote:
    def __init__(self):
        self.ip_adress = ''
        self.login = ''
        self.password = ''

class StructProcessing:
    def __init__(self):
        self.commandFile = 'cmdfile.txt'
        self.logFile = 'file.log'
        self.newStudy = True
        self.running = True
        self.overWriting = True
        self.saveIntermediateResults = False
        self.debug = 0
        self.link = 'eth0'
        self.port = 0
        self.ram = 0
        self.taskList = []
        self.remoteComputeurList = []

class StructImage:
    def __init__(self):
        self.channelOrderList = []
        self.resolution = 0.0
        self.epsg = 0
        self.nodataValue = 0

class StructRaster:
    def __init__(self):
        self.formatRaster = "GTiff"
        self.extensionRaster = ".tif"

class StructVector:
    def __init__(self):
        self.formatVector = "'ESRI Shapefile'"
        self.extensionVector = ".shp"

class StructClass:
    def __init__(self):
        self.name = ''
        self.label = 0

class StructClassification:
    def __init__(self):
        self.columnName = ''
        self.classList = []

class StructConnectionSQL_Postgis:
    def __init__(self):
        self.encoding = ''
        self.serverName = ''
        self.portNumber = 0
        self.userName = ''
        self.password = ''
        self.databaseName = ''
        self.schemaName = ''

class StructGeneral:
    def __init__(self):
        self.version = ""
        self.processing = StructProcessing()
        self.image = StructImage()
        self.raster = StructRaster()
        self.vector = StructVector()
        self.classification = StructClassification()
        self.postgis = StructConnectionSQL_Postgis()

# Task1_Print
class StructPrint_Comment:
    def __init__(self):
        self.text = ''
        self.style = ''

class StructTask1_Print:
    def __init__(self):
        self.commentsList = []

# Task2_Mail
class StructTask2_Mail:
    def __init__(self):
        self.addrMailSender = ''
        self.passwordMailSender = ''
        self.addrServerMail = ''
        self.portServerMail = 0
        self.addrMailReceivesList = []
        self.subjectOfMessage = ''
        self.messagesList = ''

# Task3_Delete
class StructTask3_Delete:
    def __init__(self):
        self.dataToCleanList = []

# Task4_Copy
class StructCopy_SrcDest:
    def __init__(self):
        self.source = ''
        self.destination = ''

class StructTask4_Copy:
    def __init__(self):
        self.dataToCopyList = []

# Task5_ReceiveFTP
class StructTask5_ReceiveFTP:
    def __init__(self):
        self.serverFtp = ''
        self.portFtp = 0
        self.loginFtp = ''
        self.passwordFtp = ''
        self.pathFtp = ''
        self.localPath = ''
        self.fileError = ''

# Task6_GenericCommand
class StructTask6_GenericCommand:
    def __init__(self):
        self.command = ''

# Task7_GenericSql
class StructSQL_InputFile:
    def __init__(self):
        self.inputFile = ''
        self.tableName = ''
        self.encoding = ''
        self.delimiter = ''
        self.columnsTypeList = []
        self.tile_size = ''
        self.overview_factor = ''

class StructSQL_outputFile:
    def __init__(self):
        self.outputFile = ''
        self.tableName = ''

class StructTask7_GenericSql:
    def __init__(self):
        self.inputFilesList = []
        self.commandsSqlList = []
        self.outputFilesList = []

# Task8_ParametricSample
class StructTask8_ParametricStudySamples :
    def __init__(self):
        self.inputVector = ''
        self.outputFile = ''
        self.outputMatrix = ''
        self.ratesList = []

# Task9_ParametricStudyTexturesIndex
class StructTask9_ParametricStudyTexturesIndices :
    def __init__(self):
        self.inputVector = ''
        self.inputSample = ''
        self.outputFile = ''
        self.outputMatrix = ''
        self.channelsList = []
        self.texturesList = []
        self.radiusList = []
        self.indicesList = []

# Task10_imagesAssembly
class StructTask10_ImagesAssembly:
    def __init__(self):
        self.empriseFile = ''
        self.sourceImagesDirList = []
        self.outputFile = ''
        self.changeZero2OtherValueBefore = False
        self.changeZero2OtherValueAfter = False
        self.changeOtherValue = 0.0
        self.dateSplitter = ''
        self.datePosition = 0
        self.dateNumberOfCharacters = 0
        self.intraDateSplitter = ''

# Task12_iansharpeningAssembly
class StructTask12_PansharpeningAssembly:
    def __init__(self):
        self.inputPanchroFile = ''
        self.inputXsFile = ''
        self.outputFile = ''
        self.interpolationMode = ''
        self.interpolationMethod = ''
        self.pansharpeningMethod = ''
        self.interpolationBco_radius = 0
        self.pansharpeningLmvm_xradius = 0
        self.pansharpeningLmvm_yradius = 0
        self.pansharpeningBayes_lambda = 0.0
        self.pansharpeningBayes_scoef = 0.0

# Task20_imageCompression
class StructTask20_ImageCompression:
    def __init__(self):
        self.inputFile = ''
        self.outputFile8b = ''
        self.outputFile8bCompress = ''
        self.Optimize8bits = False

# Task30_NeoChannelsComputation
class StructTask30_NeoChannelsComputation:
    def __init__(self):
        self.inputFilesList = []
        self.outputPath = ''
        self.channelsList = []
        self.textureFamilyList = []
        self.radiusList = []
        self.indicesList = []
        self.binNumber = 0

# StructCreation Task35 et Task50 et Task180
class StructCreation_DatabaseFile:
    def __init__(self):
        self.inputVector = ''
        self.bufferValue = 0.0
        self.sqlExpression = ''

# Task35_MnhCreation
class StructTask35_MnhCreation:
    def __init__(self):
        self.inputVector = ''
        self.inputMnsFile = ''
        self.inputMntFile = ''
        self.inputFilterFile = ''
        self.outputMnhFile = ''
        self.dataBaseRoadFileList = []
        self.dataBaseBuildFilesList = []
        self.bias = 0.0
        self.thresholdFilterFile = 0.0
        self.thresholdDeltaH = 0.0
        self.interpolationMode = ''
        self.interpolationMethod = ''
        self.interpolationBco_radius = 0
        self.simplificationPolygon = 0.0

# Task40_ChannelsConcatenantion
class StructChannelsConcatenantion_Concatenation:
    def __init__(self):
        self.stackConcatenation = False
        self.outputFile = ''
        self.encodingOutput = ''

class StructChannelsConcatenantion_Normalization:
    def __init__(self):
        self.stackNormalization = False
        self.outputFile = ''

class StructChannelsConcatenantion_Reduction:
    def __init__(self):
        self.stackReduction = False
        self.outputFile = ''
        self.method  = ''
        self.maxBandNumber = 0
        self.normalizationReduce = False
        self.napcaRadius = 0
        self.icaIterations = 0
        self.icaIncrement = 0.0

class StructTask40_ChannelsConcatenantion:
    def __init__(self):
        self.inputFilesList = []
        self.concatenation = StructChannelsConcatenantion_Concatenation()
        self.normalization = StructChannelsConcatenantion_Normalization()
        self.reduction = StructChannelsConcatenantion_Reduction()

# Task50_MacroSampleCreation
class StructMacroSampleCreation_ClassMacro:
    def __init__(self):
        self.outputVector = ''
        self.outputFile = ''
        self.name = ''
        self.dataBaseFileList = []

class StructTask50_MacroSampleCreation:
    def __init__(self):
        self.inputFile = ''
        self.inputVector = ''
        self.simplificationPolygon = 0.0
        self.classMacroSampleList = []

# Task60_MaskCreation
class StructMaskCreation_ClassMacro:
    def __init__(self):
        self.inputVector = ''
        self.outputFile = ''

class StructTask60_MaskCreation:
    def __init__(self):
        self.inputFile = ''
        self.classMacroSampleList = []

# Task70_RA_MacroSampleCutting
class StructMacroSampleCutting_ClassMacro:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''

class StructTask70_RA_MacroSampleCutting:
    def __init__(self):
        self.inputVector = ''
        self.superposition = False
        self.referenceImage = ''
        self.classMacroSampleList = []

# Task80_MacroSampleAmelioration
class StructMacroSampleAmelioration_CorrectionFile:
    def __init__(self):
        self.name = ''
        self.correctionFile = ''
        self.thresholdMin = 0.0
        self.thresholdMax = 0.0
        self.filterSizeForZero = 0
        self.filterSizeForOne = 0
        self.operatorFusion = ''

class StructMacroSampleAmelioration:
    def __init__(self):
        self.name = ''
        self.inputFile = ''
        self.outputFile = ''
        self.correctionFilesList = []

class StructTask80_MacroSampleAmelioration:
    def __init__(self):
        self.classMacroSampleList = []

# Task90_KmeansmaskApplication
class StructKmeansMaskApplication_ClassMacro:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''
        self.outputCentroidFile = ''
        self.sampling = 0
        self.label = 0

class StructTask90_KmeansMaskApplication:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''
        self.proposalTable  = ''
        self.iterations = 0
        self.propPixels = 0
        self.sizeTraining = 0
        self.minNumberTrainingSize = 0
        self.rateCleanMicroclass = 0.0
        self.rand = 0
        self.classMacroSampleList = []

# Task100_MicroSamplePolygonization
class StructMicroSamplePolygonization_InputFile:
    def __init__(self):
        self.inputFile = ''
        self.rasterErode = 0
        self.bufferSize = 0.0
        self.bufferApproximate = 0
        self.minimalArea = 0.0
        self.simplificationTolerance = 0.0

class StructTask100_MicroSamplePolygonization:
    def __init__(self):
        self.umc = 0
        self.tileSize = 0
        self.inputFileList = []
        self.outputFile = ''
        self.proposalTable = ''
        self.rateCleanMicroclass = 0.0

# Task110_ClassReallocationVector
class StructTask110_ClassReallocationVector:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''
        self.proposalTable = ''

# Task115_SampleSelectionRaster
class StructSampleSelectionRaster_RatioPerClass:
    def __init__(self):
        self.label = 0
        self.classRatio = 0.0

class StructTask115_SampleSelectionRaster:
    def __init__(self):
        self.inputFilesList = []
        self.inputSample = ''
        self.outputVector = ''
        self.outputStatisticsTable = ''
        self.samplerStrategy = ''
        self.selectRatioFloor = 0.0
        self.ratioPerClassList = []
        self.rand = 0

# Task120_SupervisedClassification
class StructTask120_SupervisedClassification:
    def __init__(self):
        self.inputFilesList = []
        self.inputVector = ''
        self.inputSample = ''
        self.outputFile = ''
        self.confidenceOutputFile = ''
        self.outputModelFile = ''
        self.inputModelFile = ''
        self.samplerMode = ''
        self.periodicJitter = 0
        self.method = ''
        self.svn_kernel = ''
        self.rf_dephTree = 0
        self.rf_numTree = 0
        self.rf_sampleMin = 0
        self.rf_terminCriteria = 0.0
        self.rf_cluster = 0
        self.rf_sizeFeatures = 0
        self.rf_obbError = 0.0

# Task125_DeepLearningClassification
class StructTask125_DeepLearningClassification:
    def __init__(self):
        self.inputFile = ''
        self.inputSample = ''
        self.inputVector = ''
        self.outputFile = ''
        self.outputModelFile = ''
        self.inputModelFile = ''
        self.gridSize = 0
        self.overflowSize = 0
        self.increaseSample = False
        self.numberClass = 0
        self.networkType = ''
        self.percentNoData = 0
        self.computeMode = ''
        self.idGpuCard = 0
        self.rand = 0
        self.nn_batch = 0
        self.nn_numberConvFilter = 0
        self.nn_kernelSize = 0
        self.nn_inOneBlock = 0
        self.nn_rateValidation = 0.0
        self.nn_numberEpoch = 0
        self.nn_earlyStoppingMonitor = ''
        self.nn_earlyStoppingPatience = 0
        self.nn_earlyStoppingMinDelta = 0.0
        self.nn_reduceLearningRateMonitor = ''
        self.nn_reduceLearningRateFactor = 0.0
        self.nn_reduceLearningRatePatience = 0
        self.nn_reduceLearningRateMinLR = 0.0

# Task130_PostTraitementsRaster
class StructPostTraitementsRaste_InputCorrectionFile:
    def __init__(self):
        self.inputFile = ''
        self.thresholdMin = 0.0
        self.thresholdMax = 0.0
        self.bufferToApply = 0
        self.inOrOut = ''
        self.classToReplace = ''
        self.replacementClass = 0

class StructTask130_PostTraitementsRaster:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''
        self.inputVector = ''
        self.inputCorrectionFileList = []

# Task140_SpecificSubSampling
class StructTask140_SpecificSubSampling:
    def __init__(self):
        self.inputFile = ''
        self.inputClassifFile = ''
        self.outputFile = ''
        self.proposalTable = ''
        self.subSamplingNumber = 0
        self.minNumberTrainingSize = 0
        self.rand = 0

# Task150_ClassRealocationRaster
class StructTask150_ClassRealocationRaster:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''
        self.proposalTable = ''

# Task160_MicroclassFusion
class StructTask160_MicroclassFusion:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''
        self.expression = ''

# Task170_MajorityFilter
class StructTask170_MajorityFilter:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''
        self.filterMode = ''
        self.radiusMajority = 0
        self.umcPixels = 0

# Task180_DataBaseSuperposition
class StructDataBaseSuperposition_ClassMacro:
    def __init__(self):
        self.label = 0
        self.dataBaseFileList = []

class StructTask180_DataBaseSuperposition:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''
        self.simplificationPolygon = 0.0
        self.classMacroSuperpositionList = []

# Task190_ClassificationRasterAssembly
class StructTask190_ClassificationRasterAssembly:
    def __init__(self):
        self.inputFilesList = []
        self.outputFile = ''
        self.inputVector = ''
        self.radius = 0
        self.valueToForce = 0

# Task200_ClassificationVectorization
class StructTask200_ClassificationVectorization:
    def __init__(self):
        self.inputFile = ''
        self.outputFile = ''
        self.inputVector = ''
        self.vectorizationType = ''
        self.expression = ''
        self.umc = 0
        self.tileSize = 0
        self.topologicalCorrectionSQL = False

# Task210_CrossingVectorRaster
class StructTask210_CrossingVectorRaster:
    def __init__(self):
        self.inputFile = ''
        self.inputVector = ''
        self.outputVector = ''
        self.bandNumber = 1
        self.statsAllCount = False
        self.statsColumnsStr = False
        self.statsColumnsReal = False

# Task210_RA_CrossingVectorRaster
class StructTask210_RA_CrossingVectorRaster:
    def __init__(self):
        self.inputClassifFile = ''
        self.inputCorrectionFile = ''
        self.inputVector = ''
        self.outputVector = ''
        self.columToAddCouvList = []
        self.columToDeleteCouvlist = []
        self.columToAddDateList = []
        self.columToAddSrcList = []
        self.classLabelDateDico = ''
        self.classLabelSrcDico = ''

# Task220_VectorRasterCutting
class StructTask220_VectorRasterCutting:
    def __init__(self):
        self.inputFilesList = []
        self.inputVectorsList = []
        self.outputFilesList = []
        self.outputVectorsList = []
        self.inputCutVector = ''
        self.overflowNbPixels = 0
        self.roundPixelSize = 0.0
        self.resamplingMethode = ''
        self.compression = False

# Task221_VectorRasterChangeEpsg
class StructTask221_VectorRasterChangeEpsg:
    def __init__(self):
        self.inputFilesList = []
        self.inputVectorsList = []
        self.outputFilesList = []
        self.outputVectorsList = []

# Task230_QualityIndicatorComputation
class StructTask230_QualityIndicatorComputation:
    def __init__(self):
        self.inputFile = ''
        self.inputVector = ''
        self.inputSample = ''
        self.outputFile = ''
        self.outputMatrix = ''

# Task240_RA_ProductOcsVerificationCorrectionSQL
class StructTask240_RA_ProductOcsVerificationCorrectionSQL:
    def __init__(self):
        self.inputEmpriseVector = ''
        self.inputVectorsList = []
        self.outputVectorsList = []

# Task250_RA_ProductOcsRasterisation
class StructTask250_RA_ProductOcsRasterisation:
    def __init__(self):
        self.inputVector = ''
        self.inputFile = ''
        self.outputFile = ''
        self.label = ''
        self.nodataOutput = 0
        self.encodingOutput = ''

# Task260_SegmentationImage
class StructTask260_SegmentationImage:
    def __init__(self):
        self.inputFile = ''
        self.outputVector = ''
        self.segmenationType = ''
        self.sms_spatialr = 0
        self.sms_ranger = 0.0
        self.sms_minsize = 0
        self.sms_tileSize = 0
        self.srm_homogeneityCriterion = ''
        self.srm_threshol = 0.0
        self.srm_nbIter = 0
        self.srm_speed = 0
        self.srm_weightSpectral = 0.0
        self.srm_weightSpatial = 0.0

# Task270_ClassificationVector
class StructTask270_ClassificationVector:
    def __init__(self):
        self.inputVector = ''
        self.outputVector = ''
        self.fieldList = []
        self.inputCfield = ''
        self.outputCfield = ''
        self.expression = ''

# Task280_GenerateOcsWithVectors
class StructTask280_GenerateOcsWithVectors:
    def __init__(self):
        self.inputText = ''
        self.outputRaster = ''
        self.codage = ''
        self.footprintVector = ''
        self.referenceRaster = ''

# Task290_RasterBandMathX
class StructTask290_RasterBandMathX:
    def __init__(self):
        self.inputFilesList = []
        self.outputFile = ''
        self.expression = ''
        self.encodingOutput = ''
        self.nodataValue = ""

# Task295_RasterSuperimpose
class StructTask295_RasterSuperimpose:
    def __init__(self):
        self.inputFileRef = ''
        self.inputFilesList = []
        self.outputFileList = []
        self.mode = ''
        self.encodingOutput = ''

# Task5_TDC_CreateEmprise
class StructTask5_TDC_CreateEmprise:
    def __init__(self):
        self.inputPath = ''
        self.outputVector = ''
        self.noAssembled = False
        self.allPolygon = False
        self.noDate = False
        self.optimisationEmprise = False
        self.optimisationNoData = False
        self.erode = 0.0
        self.dateSplitter = ''
        self.datePosition = 0
        self.dateNumberOfCharacters = 0
        self.intraDateSplitter = ''

# Task10_TDC_PolygonMerToTDC
class StructTask10_TDC_PolygonMerToTDC:
    def __init__(self):
        self.inputFile = ''
        self.ndviMaskVectorList = []
        self.outputPath = ''
        self.inputSeaPointsFile = ''
        self.inputCutVector = ''
        self.resultBinMaskVectorFunction = False
        self.simplifParameter = 0.0
        self.positiveBufferSize = 0.0
        self.negativeBufferSize = 0.0

# Task20_TDC_PrepareData
class StructTask20_TDC_PrepareData:
    def __init__(self):
        self.inputBufferTDC = ''
        self.inputVectorPaysage = ''
        self.outputPath = ''
        self.sourceImagesDirList = []
        self.idPaysage = ''
        self.idNameSubRep = ''
        self.optimisationZone = False
        self.zoneDate = False
        self.noCover = False
        self.dateSplitter = ''
        self.datePosition = 0
        self.dateNumberOfCharacters = 0
        self.intraDateSplitter = ''

# Task30_TDC_TDCSeuil
class StructTask30_TDC_TDCSeuil:
    def __init__(self):
        self.inputFile = ''
        self.sourceIndexImageThresholdsList = []
        self.outputPath = ''
        self.inputSeaPointsFile = ''
        self.inputCutVector = ''
        self.inputEmpriseVector = ''
        self.simplifParameter = 0.0
        self.calcIndiceImage = False
        self.attributeValLimite = ''
        self.attributeValProced = ''
        self.attributeValDatepr = ''
        self.attributeValPrecis = ''
        self.attributeValContac = ''
        self.attributeValType = ''
        self.attributeValReal = ''

# Task40_TDC_TDCKmeans
class StructTask40_TDC_TDCKmeans:
    def __init__(self):
        self.inputFile = ''
        self.outputPath = ''
        self.inputSeaPointsFile = ''
        self.inputCutVector = ''
        self.classesNumber = 0

# Task50_TDC_TDCClassif
class StructTDCClassif_ClassSample:
    def __init__(self):
        self.name = ''
        self.label = 0
        self.classPropertiesList = []

class StructTDCClassif_ClassMacroSuperposition:
    def __init__(self):
        self.label = 0
        self.dataBaseFileDico = {}

class StructTask50_TDC_TDCClassif:
    def __init__(self):
        self.inputFile = ''
        self.classSampleList = []
        self.outputPath = ''
        self.inputSeaPointsFile = ''
        self.inputCutVector = ''
        self.useExogenDB = False
        self.cut = False
        self.radiusMajority = 0.0
        self.microClassFusionExpression = ''
        self.step1Execution = False
        self.step2Execution = False
        self.step3Execution = False
        self.step4Execution = False
        self.exogenDBSuperp = False
        self.classMacroSuperpositionList = []

# Task60_TDC_DetectOuvrages
class StructTask60_TDC_DetectOuvrages:
    def __init__(self):
        self.inputFile = ''
        self.sourceBufferSizeThresholdIndexImageList = []
        self.outputPath = ''
        self.inputSeaPointsFile = ''
        self.inputCutVector = ''
        self.method = ''
        self.indexImageBuffers = False
        self.indexImageSobel = False

# Task70_TDC_DetectOuvragesBuffers
class StructTask70_TDC_DetectOuvragesBuffers:
    def __init__(self):
        self.inputFile = ''
        self.outputPath = ''
        self.inputCutVector = ''
        self.bufferSizeNeg = 0.0
        self.bufferSizePos = 0.0

# Task80_TDC_DetectOuvragesEdgeExtraction
class StructTask80_TDC_DetectOuvragesEdgeExtraction:
    def __init__(self):
        self.inputFile = ''
        self.sourceIndexImageThresholdsList = []
        self.outputPath = ''
        self.inputCutVector = ''
        self.calcIndexImage = False

# Task90_TDC_DistanceTDCPointLine
class StructTask90_TDC_DistanceTDCPointLine:
    def __init__(self):
        self.inputPointsFile = ''
        self.inputTDCFile = ''
        self.outputPath = ''
        self.inputSeaPointsFile = ''
        self.evolColumnName = ''

# Task100_TDC_DistanceTDCBuffers
class StructTask100_TDC_DistanceTDCBuffers:
    def __init__(self):
        self.inputReferenceFile = ''
        self.inputCalculatedFile = ''
        self.outputPath = ''
        self.inputSeaPointsFile = ''
        self.bufferSize = 0.0
        self.buffersNumber = 0.0

# Task110_TDC_PostTreatmentTDC
class StructTask110_TDC_PostTreatmentTDC:
    def __init__(self):
        self.inputVectorsList = []
        self.inputRockyVector = ''
        self.outputVectorTdcAll = ''
        self.outputVectorTdcWithoutRocky = ''
        self.generalize_method = ''
        self.generalize_threshold = 0
        self.fusionColumnName = ''

# TaskUCZ_ClassificationUCZ
class StructTaskUCZ_ClassificationUCZ:
    def __init__(self):
        self.inputVector = ''
        self.outputVector = ''
        self.empriseVector = ''
        self.binaryVegetationMask = ''
        self.satelliteImage = ''
        self.digitalHeightModel = ''
        self.builtsVectorList = []
        self.hydrographyVector = ''
        self.roadsVectorList = []
        self.rpgVector = ''
        self.indicatorsTreatmentChoice = ''
        self.uczTreatmentChoice = ''
        self.dbmsChoice = ''
        self.ndviThreshold = 0
        self.ndviWaterThreshold = 0
        self.ndwi2Threshold = 0
        self.biLowerThreshold = 0
        self.biUpperThreshold = 0

# Task00_LCZ_DataPreparation
class StructDataPreparation_BuiltInput:
    def __init__(self):
        self.builtInput = ''

class StructTask00_LCZ_DataPreparation:
    def __init__(self):
        self.empriseFile = ''
        self.gridInput = ''
        self.builtInputList = []
        self.roadsInputList = []
        self.classifInput = ''
        self.mnsInput = ''
        self.mnhInput = ''
        self.gridOutput = ''
        self.gridOutputCleaned = ''
        self.builtOutput = ''
        self.roadsOutput = ''
        self.classifOutput = ''
        self.mnsOutput = ''
        self.mnhOutput = ''
        self.colCodeUA = ''
        self.colItemUA = ''

# Task10_LCZ_BuildingSurfaceFraction
class StructTask10_LCZ_BuildingSurfaceFraction:
    def __init__(self):
        self.inputGridFile = ''
        self.outputGridFile = ''
        self.inputClassifFile = ''
        self.buildingClassLabelList = []

# Task20_LCZ_ImperviousSurfaceFraction
class StructTask20_LCZ_ImperviousSurfaceFraction:
    def __init__(self):
        self.inputGridFile = ''
        self.outputGridFile = ''
        self.inputClassifFile = ''
        self.imperviousClassLabelList = []

# Task30_LCZ_PerviousSurfaceFraction
class StructTask30_LCZ_PerviousSurfaceFraction:
    def __init__(self):
        self.inputGridFile = ''
        self.outputGridFile = ''
        self.inputClassifFile = ''
        self.perviousClassLabelList = []

# Task40_LCZ_SkyViewFactor
class StructTask40_LCZ_SkyViewFactor:
    def __init__(self):
        self.inputGridFile = ''
        self.outputGridFile = ''
        self.inputMnsFile = ''
        self.inputClassifFile = ''
        self.buildingClassLabelList = []
        self.dimGridX = 0
        self.dimGridY = 0
        self.radius = 0
        self.method = 0
        self.dlevel = 0
        self.ndirs = 0

# Task50_LCZ_HeightOfRoughnessElements
class StructTask50_LCZ_HeightOfRoughnessElements:
    def __init__(self):
        self.inputGridFile = ''
        self.outputGridFile = ''
        self.inputBuiltFile = ''
        self.heightField = ''
        self.idField = ''
        self.inputMnhFile = ''
        self.inputClassifFile = ''
        self.buildingClassLabelList = []

# Task60_LCZ_TerrainRoughnessClass
class StructTask60_LCZ_TerrainRoughnessClass:
    def __init__(self):
        self.inputGridFile = ''
        self.outputGridFile = ''
        self.inputBuiltFile = ''
        self.distanceLines = 0

# Task70_LCZ_AspectRatio
class StructTask70_LCZ_AspectRatio:
    def __init__(self):
        self.inputGridFile = ''
        self.outputGridFile = ''
        self.inputRoadsFile = ''
        self.inputBuiltFile = ''
        self.segDist = 0
        self.segLength = 0
        self.bufferSize = 0

# Task80_LCZ_OcsIndicators
class StructTask80_LCZ_OcsIndicators:
    def __init__(self):
        self.inputGridVector = ''
        self.outputGridVector = ''
        self.inputClassifVector = ''
        self.fieldClassifName = ''
        self.inputMnhFile = ''
        self.inputClassifFile = ''
        self.buildingClassLabelList = []
        self.roadClassLabelList = []
        self.baresoilClassLabelList = []
        self.waterClassLabelList = []
        self.vegetationClassLabelList = []
        self.hightVegetationClassLabelList = []
        self.lowVegetationClassLabelList = []

# Task90_LCZ_ClassificationLCZ
class StructClassificationLCZ_VariablesValuesTree:
    def __init__(self):
        self.variable = ''
        self.value = 0.0

class StructClassificationLCZ_IndiceFile:
    def __init__(self):
        self.indiceFile = ''
        self.indicator = ''
        self.columnSrc = ''
        self.abbreviation = ''

class StructTask90_LCZ_ClassificationLCZ:
    def __init__(self):
        self.inputPythonFile = ''
        self.inputFile = ''
        self.outputFile = ''
        self.variablesValuesTreeList = []
        self.useClassifRf = False
        self.nbSampleRf = 0
        self.modelRfFile = ''
        self.columnNameId = ''
        self.columnNameUaCode = ''
        self.columnNameLczHisto = ''
        self.columnNameLcz = ''
        self.columnNameLczRf = ''
        self.indiceFilesList = []

# Task95_LCZ_ClassificationLczOperational
class StructTask95_LCZ_ClassificationLczOperational:
    def __init__(self):
        self.inputDivisionFile = ''
        self.inputHreFile = ''
        self.inputOcsFile = ''
        self.outputLczFile = ''
        self.columnNameId = ''

# Task10_RSQ_WaterHeight
class StructTask10_RSQ_WaterHeight:
    def __init__(self):
        self.inputFloodedAreasVector = ''
        self.inputDigitalElevationModelFile = ''
        self.outputHeightsClassesFile = ''
        self.outputHeightsClassesVector = ''
        self.heightsClasses = ''
        self.grass_environmentVariable = ''
        self.grass_databaseName = ''
        self.grass_location = ''
        self.grass_mapset = ''

# Task20_RSQ_AreasUnderUrbanization
class StructTask20_RSQ_AreasUnderUrbanization:
    def __init__(self):
        self.inputPlotVector = ''
        self.outputPlotVector = ''
        self.footprintVector = ''
        self.inputBuiltFile = ''
        self.inputBuiltVectorsList = []
        self.inputPluVector = ''
        self.inputPprVector = ''
        self.minBuiltSizesList = []
        self.pluField = ''
        self.pluUValuesList = []
        self.pluAuValuesList = []
        self.pprField = ''
        self.pprRedValuesList = []
        self.pprBlueValuesList = []

# Task30_RSQ_EvolutionOverTime
class StructTask30_RSQ_EvolutionOverTime:
    def __init__(self):
        self.inputPlotVector = ''
        self.outputPlotVector = ''
        self.footprintVector = ''
        self.inputTxFilesList = []
        self.evolutionsList = []

# Task40_RSQ_UhiVulnerability
class StructTask40_RSQ_UhiVulnerability:
    def __init__(self):
        self.inputDivisionVector = ''
        self.footprintVector = ''
        self.populationVector = ''
        self.builtVector = ''
        self.outputVulnerabilityVector = ''
        self.idDivisionField = ''
        self.idPopulationField = ''
        self.idBuiltField = ''
        self.stakeField = ''
        self.healthVulnFieldsList = []
        self.socialVulnFieldsList = []
        self.heightField = ''
        self.builtSqlFilter = ''

# Ensemble des tasks
class StructTasks:
    def __init__(self):
        self.task1_Print = []
        self.task2_Mail = []
        self.task3_Delete = []
        self.task4_Copy = []
        self.task5_ReceiveFTP = []
        self.task6_GenericCommand = []
        self.task7_GenericSql = []
        self.task8_ParametricStudySamples = None
        self.task9_parametricStudyTexturesIndices = None
        self.task10_ImagesAssembly = []
        self.task12_PansharpeningAssembly = []
        self.task20_ImageCompression = []
        self.task30_NeoChannelsComputation = []
        self.task35_MnhCreation = []
        self.task40_ChannelsConcatenantion = []
        self.task50_MacroSampleCreation = []
        self.task60_MaskCreation = []
        self.task70_RA_MacroSampleCutting = []
        self.task80_MacroSampleAmelioration = []
        self.task90_KmeansMaskApplication = []
        self.task100_MicroSamplePolygonization = []
        self.task110_ClassReallocationVector = []
        self.task115_SampleSelectionRaster = []
        self.task120_SupervisedClassification = []
        self.task125_DeepLearningClassification = []
        self.task130_PostTraitementsRaster = []
        self.task140_SpecificSubSampling = []
        self.task150_ClassRealocationRaster = []
        self.task160_MicroclassFusion = []
        self.task170_MajorityFilter = []
        self.task180_DataBaseSuperposition = []
        self.task190_ClassificationRasterAssembly = []
        self.task200_ClassificationVectorization = []
        self.task210_CrossingVectorRaster = []
        self.task210_RA_CrossingVectorRaster = []
        self.task220_VectorRasterCutting = []
        self.task221_VectorRasterChangeEpsg = []
        self.task230_QualityIndicatorComputation = []
        self.task240_RA_ProductOcsVerificationCorrectionSQL = []
        self.task250_RA_ProductOcsRasterisation = []
        self.task260_SegmentationImage = []
        self.task270_ClassificationVector = []
        self.task280_GenerateOcsWithVectors = []
        self.task290_RasterBandMathX = []
        self.task295_RasterSuperimpose = []
        self.task5_TDC_CreateEmprise = []
        self.task10_TDC_PolygonMerToTDC = []
        self.task20_TDC_PrepareData = []
        self.task30_TDC_TDCSeuil = []
        self.task40_TDC_TDCKmeans = []
        self.task50_TDC_TDCClassif = []
        self.task60_TDC_DetectOuvrages = []
        self.task70_TDC_DetectOuvragesBuffers = []
        self.task80_TDC_DetectOuvragesEdgeExtraction = []
        self.task90_TDC_DistanceTDCPointLine = []
        self.task100_TDC_DistanceTDCBuffers = []
        self.task110_TDC_PostTreatmentTDC = []
        self.taskUCZ_ClassificationUCZ = []
        self.task00_LCZ_DataPreparation = []
        self.task10_LCZ_BuildingSurfaceFraction = []
        self.task20_LCZ_ImperviousSurfaceFraction = []
        self.task30_LCZ_PerviousSurfaceFraction = []
        self.task40_LCZ_SkyViewFactor = []
        self.task50_LCZ_HeightOfRoughnessElements = []
        self.task60_LCZ_TerrainRoughnessClass = []
        self.task70_LCZ_AspectRatio = []
        self.task80_LCZ_OcsIndicators = []
        self.task90_LCZ_ClassificationLCZ = []
        self.task95_LCZ_ClassificationLczOperational = []
        self.task10_RSQ_WaterHeight = []
        self.task20_RSQ_AreasUnderUrbanization = []
        self.task30_RSQ_EvolutionOverTime = []
        self.task40_RSQ_UhiVulnerability = []

# La structure settings
class StructSettings:
    def __init__(self):
        self.general = StructGeneral()
        self.tasks = StructTasks()
