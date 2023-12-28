from flask import Flask, request, jsonify, render_template
import math
import random
import redis
import time
import json
from azure.cosmos import CosmosClient 
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

app = Flask(__name__)

# Replace with your Azure Cosmos DB connection details
endpoint = 'https://tutorial-uta-cse6332.documents.azure.com:443/'
key = 'fSDt8pk5P1EH0NlvfiolgZF332ILOkKhMdLY6iMS2yjVqdpWx4XtnVgBoJBCBaHA8PIHnAbFY4N9ACDbMdwaEw=='

# Replace with your database and container names
database_id = 'tutorial'
container_id = 'us_cities'
container_id_reviews = 'reviews'

client = CosmosClient(endpoint, key)
database = client.get_database_client(database_id)
container = database.get_container_client(container_id)
container_reviews = database.get_container_client(container_id_reviews)

# Redis cache connection information
redis_passwd = "b9Q42F5LUEahwEb2D6HCbXLzTcIupxtPtAzCaEpdjYE="
redis_host = "tutorial-uta-cse6332-redis.redis.cache.windows.net"
redis_port = 6380

# Connect to Redis cache
cache = redis.StrictRedis(
    host=redis_host,
    port=redis_port,
    db=0,
    password=redis_passwd,
    ssl=True,
)



# Variable to store caching status
use_cache = False

def toggle_cache_status():
    global use_cache
    use_cache = not use_cache
    return use_cache

@app.route('/toggle_cache', methods=['GET'])
def toggle_cache():
    status = toggle_cache_status()
    return jsonify({'status': status})

@app.route('/get_distances', methods=['GET'])
def get_distances():
    start_time = time.time()

    city_name = request.args.get('cityName')
    state_name = request.args.get('stateName')
    page_size = int(request.args.get('pageSize', 50))
    page_number = int(request.args.get('page', 1))
    print(page_number)

    if use_cache:
        cache_key = f"distances_{city_name}_{state_name}"
        cached_result = cache.get(cache_key)

        if cached_result:
            result = json.loads(cached_result)
            result['cacheHit'] = True
            result['computationTime'] = (time.time()-start_time)*1000  # Actual time not needed for cached results
            return jsonify(result)

    # Query given city coordinates
    city_query = f"SELECT c.lat, c.lng FROM c WHERE c.city = '{city_name}' AND c.state = '{state_name}'"
    city_coordinates = list(container.query_items(query=city_query, enable_cross_partition_query=True))

    if not city_coordinates:
        return jsonify({'error': 'City not found'}), 404

    city_coordinate = city_coordinates[0]
    lat, lng = float(city_coordinate['lat']), float(city_coordinate['lng'])

    # Query coordinates of all other cities and sort by Euclidean distance
    all_cities_query = f"SELECT c.city, c.lat, c.lng FROM c WHERE c.city != '{city_name}' AND c.state = '{state_name}'"
    all_cities = list(container.query_items(query=all_cities_query, enable_cross_partition_query=True))

    # Calculate and store the sorted distances along with city names
    sorted_distances = [{'city': c['city'], 'distance': math.sqrt((lat - float(c['lat']))**2 + (lng - float(c['lng']))**2)} for c in all_cities]
    sorted_distances = sorted(sorted_distances, key=lambda x: x['distance'])

    # Pagination
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    paginated_distances = sorted_distances[start_idx:end_idx]

    end_time = time.time()
    computation_time = int((end_time - start_time) * 1000)
    distances = []
    for entry in paginated_distances:
        distances.append([entry['city'],entry['distance']])
    result = {
        'distances':distances,
        'computationTime': computation_time,
        'cacheHit': False
    }
    print(result)

    if use_cache:
        # Store result in Redis cache
        cache_key = f"distances_{city_name}_{state_name}_{page_size}_{page_number}"
        cache.setex(cache_key, 3600, json.dumps(result))  # Cache result for 1 hour

    return jsonify(result)





stopwords_file_path = 'stopwords.txt'

def read_stopwords_from_file(file_path):
    with open(file_path, 'r') as file:
        stopwords = [line.strip() for line in file]
    return set(stopwords)

# Replace 'your_stopwords_file.txt' with the actual path to your stopwords file
stopwords_file_path = 'stopwords.txt'
stopwords = read_stopwords_from_file(stopwords_file_path)

# Merge the provided stopwords with the default English stopwords
stopwords = stopwords.union(ENGLISH_STOP_WORDS)

# Function to perform KNN clustering on reviews
def knn_reviews_clustering(classes, k_value, words):
    # Retrieve cities and reviews from Cosmos DB
    query_cities = "SELECT  c.city, c.population, c.lat, c.lng FROM c"
    cities = list(container.query_items(query=query_cities, enable_cross_partition_query=True))

    query_reviews = "SELECT  r.city, r.review FROM r"
    reviews = list(container_reviews.query_items(query=query_reviews, enable_cross_partition_query=True))

    # Extract relevant data
    city_data = [(city['city'], city['population'], (city['lat'], city['lng'])) for city in cities]
    review_data = [(review['city'], review['review'].lower()) for review in reviews]

    # Prepare TF-IDF matrix
    vectorizer = TfidfVectorizer(stop_words=stopwords, max_features=words)
    tfidf_matrix = vectorizer.fit_transform([review[1] for review in review_data])
    tfidf_matrix_normalized = normalize(tfidf_matrix)

    # Use Nearest Neighbors to find K nearest neighbors for each city
    nn_model = NearestNeighbors(n_neighbors=k_value)
    nn_model.fit(tfidf_matrix_normalized)
    distances, indices = nn_model.kneighbors(tfidf_matrix_normalized)

    # Generate sample result
    result = {
        'classes': classes,
        'k': k_value,
        'words': words,
        'clusters': []
    }

    for cluster_label in range(classes):
        cluster_indices = [i for i in range(len(indices)) if cluster_label in indices[i]]
        cluster_reviews = [review_data[i] for i in cluster_indices]

        # Placeholder: Calculate weighted average score
        weighted_avg_score = sum(int(city[1]) for city in city_data if city[0] in [review[0] for review in cluster_reviews]) / len(cluster_reviews)

        # Placeholder: Extract most popular words
        popular_words = vectorizer.get_feature_names_out()

        # Placeholder: Extract center city
        center_city = city_data[cluster_indices[0]][0] if cluster_indices else None

        result['clusters'].append({
            'centerCity': center_city,
            'citiesInCluster': [review[0] for review in cluster_reviews],
            'popularWords': popular_words,
            'weightedAverageScore': weighted_avg_score
        })

    return jsonify(result)

@app.route('/stat/knn_reviews', methods=['GET'])
def knn_reviews():
    start_time = time.time()

    classes = int(request.args.get('classes', 6))
    k_value = int(request.args.get('k', 3))
    words = int(request.args.get('words', 100))

    if use_cache:
        cache_key = f"knn_reviews_{classes}_{k_value}_{words}"
        cached_result = cache.get(cache_key)

        if cached_result:
            result = json.loads(cached_result)
            result['cacheHit'] = True
            result['computationTime'] = 0  # Actual time not needed for cached results
            return jsonify(result)

    result = knn_reviews_clustering(classes, k_value, words)

    end_time = time.time()
    computation_time = (end_time - start_time) * 1000

    result['computationTime'] = computation_time
    result['cacheHit'] = False

    if use_cache:
        # Store result in Redis cache
        cache_key = f"knn_reviews_{classes}_{k_value}_{words}"
        cache.setex(cache_key, 3600, json.dumps(result))  # Cache result for 1 hour

    return jsonify(result)




def calculate_distance(lat1, lng1, lat2, lng2):
    return math.sqrt((lat1 - lat2)**2 + (lng1 - lng2)**2)

# Function to get average review scores and sort by distance
# @app.route('/get_average_review_scores', methods=['GET'])
def get_average_review_scores(city_name,state_name):
    # start_time = time.time()

    # city_name = request.args.get('cityName')
    # state_name = request.args.get('stateName')
    # print(city_name)

    query_cities = 'SELECT c.city, c.state, c.lat, c.lng FROM c'
    cities = list(container.query_items(query=query_cities, enable_cross_partition_query=True))

    query_reviews = 'SELECT  r.city, r.review, r.score FROM r'
    reviews = list(container_reviews.query_items(query=query_reviews, enable_cross_partition_query=True))


    city_coords = [city for city in cities if city['city'] == city_name and city['state'] == state_name]
    if not city_coords:
        return jsonify({'error': 'City not found'}), 404

    lat, lng = float(city_coords[0]['lat']), float(city_coords[0]['lng'])

    # distances = [{'city': c['city'], 'distance': math.sqrt((lat - float(c['lat']))**2 + (lng - float(c['lng']))**2)} for c in cities]
    # distances = sorted(distances, key=lambda x: x['distance'])

    # avg_review_scores = {}
    # for distance in distances:
    #     city_name = distance['city']
    #     scores_for_city = [review['score'] for review in reviews if review['city'] == city_name]
      
    #     if scores_for_city:
    #         avg_score = sum(map(int, scores_for_city)) / len(scores_for_city)
    #         print(avg_score)
    #         avg_review_scores[city_name] = avg_score
    city_scores = {}
    for review in reviews:
        city_lower = review['city'].lower()
        if city_lower in city_scores:
            city_scores[city_lower].append(review['score'])
        else:
            city_scores[city_lower] = [review['score']]

    # Calculate average scores
    avg_scores = {city: sum(float(score) for score in scores) / len(scores) if scores else 0 for city, scores in city_scores.items()}

    distances = []
    for city in cities:
        if city['city'].lower() != city_name.lower():
            distance = math.sqrt((lat - float(city['lat']))**2 + (lng - float(city['lng']))**2) 
            avg_score = avg_scores.get(city['city'].lower(), 0)
            distances.append({
                'city_name': city['city'],
                'distance': distance,
                'score': avg_score
            })

    # Sort by distance
    sorted_cities = sorted(distances, key=lambda x: x['distance'])


    # Paginate the results (10 cities per page)
    page = int(request.args.get('page', 1))
    page_size = 10
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_distances = distances[start_idx:end_idx]
    # paginated_avg_review_scores = {entry['city']: avg_review_scores.get(entry['city'], 0) for entry in paginated_distances}

    # return {'distances': paginated_distances, 'scores': paginated_avg_review_scores}
    return paginated_distances

# Route to handle the average review scores request
@app.route('/get_average_review_scores', methods=['GET'])
def get_average_review_scores_route():
    start_time = time.time()

    city_name = request.args.get('cityName')
    state_name = request.args.get('stateName')

    result = get_average_review_scores(city_name, state_name)

    end_time = time.time()
    computation_time = int((end_time - start_time) * 1000)

    result_with_time = {
        'scores': result,
        'computationTime': computation_time
    }

    return jsonify(result_with_time)

@app.route('/flush_cache', methods=['POST'])
def flush_cache():
    cache.flushdb()
    return jsonify({'status': 'Cache flushed successfully'})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
