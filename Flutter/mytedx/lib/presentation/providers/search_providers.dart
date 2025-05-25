
import 'dart:convert'; // Per jsonDecode se necessario, ma qui è per Map<String, dynamic>

class SearchedTalk {
  final String id;
  final String title;
  final String details; // Mappato da 'description' nel JSON
  final String slug;
  final String mainSpeaker; // Mappato da 'speakers' nel JSON
  final String url;
  final List<String> tags; // Mappato da 'tags' nel JSON
  final String? publishedAt; // Può essere null, o una stringa data
  final int? duration; // Può essere null o un intero

  SearchedTalk({
    required this.id,
    required this.title,
    required this.details,
    required this.slug,
    required this.mainSpeaker,
    required this.url,
    required this.tags,
    this.publishedAt,
    this.duration,
  });

  factory SearchedTalk.fromJSON(Map<String, dynamic> jsonMap) {
    // Gestione di 'id' con fallback, come nell'esempio originale
    String determineId(Map<String, dynamic> map) {
      if (map['id'] != null) {
        return map['id'].toString();
      }
      // Fallback se id è null o mancante, come nel tuo codice originale
      return DateTime.now().millisecondsSinceEpoch.toString();
    }

    // Estrazione e parsing di 'tags'
    List<String> parseTags(dynamic tagsData) {
      if (tagsData is List) {
        // Assicurati che ogni elemento sia una stringa
        return tagsData.map((tag) => tag.toString()).toList();
      }
      return []; // Restituisce una lista vuota se 'tags' non è una lista o è null
    }

    // Estrazione e parsing di 'duration'
    int? parseDuration(dynamic durationData) {
      if (durationData is int) {
        return durationData;
      }
      if (durationData is String) {
        return int.tryParse(durationData);
      }
      return null; // Restituisce null se non è un intero o una stringa parsabile
    }

    return SearchedTalk(
      id: determineId(jsonMap),
      title: jsonMap['title']?.toString() ?? 'No Title',
      details: jsonMap['description']?.toString() ?? 'No Description', // Mappato da 'description'
      slug: jsonMap['slug']?.toString() ?? '',
      mainSpeaker: jsonMap['speakers']?.toString() ?? 'Unknown Speaker', // Mappato da 'speakers'
      url: jsonMap['url']?.toString() ?? '',
      tags: parseTags(jsonMap['tags']),
      publishedAt: jsonMap['publishedAt']?.toString(), // Sarà una stringa ISO, o null
      duration: parseDuration(jsonMap['duration']),
    );
  }

  // Opzionale: Metodo toJson per la serializzazione (se necessario)
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': details, // Mappa 'details' di nuovo a 'description' per coerenza con il JSON
      'slug': slug,
      'speakers': mainSpeaker, // Mappa 'mainSpeaker' di nuovo a 'speakers'
      'url': url,
      'tags': tags,
      'publishedAt': publishedAt,
      'duration': duration,
    };
  }

  // Opzionale: Metodo copyWith (utile per la gestione dello stato immutabile)
  SearchedTalk copyWith({
    String? id,
    String? title,
    String? details,
    String? slug,
    String? mainSpeaker,
    String? url,
    List<String>? tags,
    String? publishedAt,
    int? duration,
  }) {
    return SearchedTalk(
      id: id ?? this.id,
      title: title ?? this.title,
      details: details ?? this.details,
      slug: slug ?? this.slug,
      mainSpeaker: mainSpeaker ?? this.mainSpeaker,
      url: url ?? this.url,
      tags: tags ?? this.tags,
      publishedAt: publishedAt ?? this.publishedAt,
      duration: duration ?? this.duration,
    );
  }

  // Opzionale: Override di toString, equals e hashCode per un debug e confronto più semplici
  @override
  String toString() {
    return 'SearchedTalk(id: $id, title: $title, details: $details, slug: $slug, mainSpeaker: $mainSpeaker, url: $url, tags: $tags, publishedAt: $publishedAt, duration: $duration)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
  
    return other is SearchedTalk &&
      other.id == id &&
      other.title == title &&
      other.details == details &&
      other.slug == slug &&
      other.mainSpeaker == mainSpeaker &&
      other.url == url &&
      // Confronto profondo per liste
      (other.tags.length == tags.length && other.tags.asMap().entries.every((entry) => tags[entry.key] == entry.value)) &&
      other.publishedAt == publishedAt &&
      other.duration == duration;
  }

  @override
  int get hashCode {
    return id.hashCode ^
      title.hashCode ^
      details.hashCode ^
      slug.hashCode ^
      mainSpeaker.hashCode ^
      url.hashCode ^
      tags.fold(0, (prev, element) => prev ^ element.hashCode) ^ // Semplice hash per la lista
      publishedAt.hashCode ^
      duration.hashCode;
  }
}