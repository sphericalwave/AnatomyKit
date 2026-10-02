//
//  LegacyFixtures.swift
//  AnatomyKitTests
//
//  Every string torque and suit persisted before AnatomyKit, frozen as of
//  2026-10-02. Copied from the app sources, not from aliases.json, so a
//  missing alias fails here. Append when an app ships a new string; never
//  delete.
//

enum LegacyFixtures {
    /// torque `Movement.rawValue`.
    static let torqueMovements = [
        "tmj.depress", "tmj.elevate", "tmj.protrude", "tmj.retrude",
        "tmj.lateralDeviation", "cervical.flex", "cervical.extend", "cervical.lateralFlex",
        "cervical.rotate", "cervical.protract", "cervical.retract", "thoracic.flex",
        "thoracic.extend", "thoracic.lateralFlex", "thoracic.rotate", "lumbar.flex",
        "lumbar.extend", "lumbar.lateralFlex", "lumbar.rotate", "scapula.elevate",
        "scapula.depress", "scapula.protract", "scapula.retract", "scapula.upwardRotate",
        "scapula.downwardRotate", "gh.flex", "gh.extend", "gh.abduct",
        "gh.adduct", "gh.internalRotate", "gh.externalRotate", "gh.horizontalAbduct",
        "gh.horizontalAdduct", "elbow.flex", "elbow.extend", "forearm.pronate",
        "forearm.supinate", "wrist.flex", "wrist.extend", "wrist.radialDeviate",
        "wrist.ulnarDeviate", "fingers.mcpFlex", "fingers.mcpExtend", "fingers.abduct",
        "fingers.adduct", "fingers.ipFlex", "fingers.ipExtend", "thumb.flex",
        "thumb.extend", "thumb.abduct", "thumb.adduct", "thumb.oppose",
        "thumb.ipFlex", "thumb.ipExtend", "hip.flex", "hip.extend",
        "hip.abduct", "hip.adduct", "hip.internalRotate", "hip.externalRotate",
        "knee.flex", "knee.extend", "knee.internalRotate", "knee.externalRotate",
        "ankle.dorsiflex", "ankle.plantarflex", "subtalar.invert", "subtalar.evert",
        "bigToe.flex", "bigToe.extend", "toes.flex", "toes.extend",
    ]

    /// SuitKit `Joint.rawValue`.
    static let suitJoints = [
        "jaw", "neck", "shoulder", "elbow",
        "wrist", "hand", "thoracicSpine", "lumbarSpine",
        "sacroiliac", "hip", "knee", "ankle",
        "foot",
    ]

    /// SuitKit `AnatomyTrainLine.rawValue`.
    static let suitTrainLines = [
        "superficialBack", "superficialFront", "lateral",
        "spiral", "deepFront", "superficialBackArm",
        "deepBackArm", "superficialFrontArm", "deepFrontArm",
        "backFunctional", "frontFunctional", "ipsilateralFunctional",
    ]

    /// SuitKit `AnatomyRegion.rawValue`.
    static let suitRegions = [
        "headNeck", "torso", "arm", "leg",
    ]

    /// SuitKit `AnatomyNode.nodeName` (standard catalog).
    static let suitMuscles = [
        "occipitofrontalis", "sternocleidomastoid", "splenius_capitis",
        "longus_colli", "scalenus_anterior", "digastric",
        "trapezius", "latissimus_dorsi", "rhomboid_major",
        "levator_scapulae", "serratus_anterior", "erector_spinae",
        "quadratus_lumborum", "psoas_major", "iliacus",
        "diaphragm", "transversus_abdominis", "rectus_abdominis",
        "external_oblique", "internal_oblique", "intercostals",
        "pectoralis_major", "pectoralis_minor", "supraspinatus",
        "infraspinatus", "teres_minor", "teres_major",
        "subscapularis", "levator_ani", "deltoid",
        "coracobrachialis", "biceps_brachii", "brachialis",
        "triceps_brachii", "brachioradialis", "supinator",
        "pronator_teres", "extensor_carpi_radialis_longus", "extensor_digitorum",
        "flexor_carpi_radialis", "flexor_digitorum_superficialis", "abductor_pollicis_brevis",
        "abductor_digiti_minimi_manus", "gluteus_maximus", "gluteus_medius",
        "gluteus_minimus", "tensor_fasciae_latae", "piriformis",
        "sartorius", "rectus_femoris", "vastus_lateralis",
        "vastus_medialis", "biceps_femoris", "semitendinosus",
        "semimembranosus", "adductor_magnus", "adductor_longus",
        "adductor_brevis", "pectineus", "gracilis",
        "popliteus", "gastrocnemius", "soleus",
        "tibialis_anterior", "tibialis_posterior", "fibularis_longus",
        "extensor_digitorum_longus", "flexor_hallucis_longus", "flexor_digitorum_brevis",
        "sacrotuberous_ligament",
    ]
}
