class Talk {
  final String
  id; // Aggiunto ID, presumendo che il backend lo fornisca (es. da MongoDB _id)
  final String title;
  final String details; // description
  final String slug;
  final String mainSpeaker; // speakers
  final String url;
  final List<String> keyPhrases;
  final String? publishedAt; // Aggiunto, se disponibile
  final int? duration; // Aggiunto, se disponibile

  Talk({
    required this.id,
    required this.title,
    required this.details,
    required this.slug,
    required this.mainSpeaker,
    required this.url,
    this.keyPhrases = const [],
    this.publishedAt,
    this.duration,
  });

  factory Talk.fromJSON(Map<String, dynamic> jsonMap) {
    // L'API Get_Talks_By_ID sembra usare 'id' (numerico?) come chiave primaria nel CSV
    // ma poi il documento finale MongoDB ha '_id' (stringa).
    // La Lambda Get_Talks_By_ID probabilmente restituisce l'ID che Flutter deve usare.
    // Se la lambda restituisce '_id' per identificare univocamente un talk, usalo.
    // Se restituisce 'id' numerico e poi il dettaglio usa '_id' stringa, potrebbe servire una mappatura.
    // Per ora assumo che 'id' o '_id' sia presente e univoco.
    // L'API Get_Talks_By_ID fornita usa campi come 'title', 'description', ecc.
    // Il campo 'id' che viene inviato alla lambda GetTalkSummary o GetRelatedTalks
    // deve corrispondere all'ID del talk in Neo4j e MongoDB.
    // Assumiamo che la Lambda Get_Talks_By_ID restituisca un campo 'id' o '_id' utilizzabile.
    // Il tuo modello originale non aveva un campo ID, che è cruciale.

    String determineId(Map<String, dynamic> json) {
      if (json.containsKey('id') && json['id'] != null)
        return json['id'].toString();
      // Se nessun ID è presente, potrebbe essere un problema.
      // Per ora, generiamo un placeholder, ma dovresti assicurarti che l'API fornisca un ID.
      print(
        "WARNING: Talk.fromJSON: Missing '_id' or 'id' field. Using slug as fallback ID.",
      );
      return json['slug'] ?? DateTime.now().millisecondsSinceEpoch.toString();
    }

    return Talk(
      id: determineId(jsonMap),
      title: jsonMap['title'] ?? 'No Title',
      details:
          jsonMap['description'] ??
          jsonMap['details'] ??
          'No Description', // Aggiunto fallback per 'details'
      slug: (jsonMap['slug'] ?? ""),
      mainSpeaker:
          (jsonMap['speakers'] ??
              jsonMap['mainSpeaker'] ??
              "Unknown Speaker"), // Aggiunto fallback per 'mainSpeaker'
      url: (jsonMap['url'] ?? ""),
      keyPhrases:
          (jsonMap['comprehend_analysis']?['KeyPhrases'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          (jsonMap['keyPhrases']
                  as List<
                    dynamic
                  >?) // Fallback se keyPhrases è al primo livello
              ?.map((e) => e.toString())
              .toList() ??
          [],
      publishedAt: jsonMap['publishedAt']?.toString(),
      duration:
          jsonMap['duration'] is int
              ? jsonMap['duration']
              : (jsonMap['duration'] is String
                  ? int.tryParse(jsonMap['duration'])
                  : null),
    );
  }
}
