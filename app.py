# app.py
from flask import Flask, request, jsonify, render_template
import pandas as pd

app = Flask(__name__)

# Load data files
reviews_df = pd.read_csv('amazon-reviews.csv')
cities_df = pd.read_csv('us-cities.csv')

# Merge data on the 'city' key
merged_df = pd.merge(reviews_df, cities_df, on='city', how='inner')

@app.route('/popular_words', methods=['GET'])
def popular_words():
    city_name = request.args.get('city', None)
    limit = int(request.args.get('limit', 10))

    # Filter data based on the given city name
    if city_name:
        filtered_df = merged_df[merged_df['city'] == city_name]
    else:
        filtered_df = merged_df

    # Count word popularity based on the number of reviews
    word_popularity = filtered_df['review'].str.split(expand=True).stack().value_counts()

    # Create response
    response = [{'term': term, 'popularity': int(popularity)} for term, popularity in word_popularity.items()]

    # Sort by popularity in descending order
    response = sorted(response, key=lambda x: x['popularity'], reverse=True)

    # Return the top N words or all if less than N
    response = response[:limit]

    return jsonify(response)

@app.route('/popular_words_population', methods=['GET'])
def popular_words_population():
    city_name = request.args.get('city', None)
    limit = int(request.args.get('limit', 10))

    # Filter data based on the given city name
    if city_name:
        filtered_df = merged_df[merged_df['city'] == city_name]
    else:
        filtered_df = merged_df

    # Count word popularity based on the sum of population
    word_popularity = filtered_df.groupby('review')['population'].sum()

    # Create response
    response = [{'term': term, 'popularity': int(popularity)} for term, popularity in word_popularity.iteritems()]

    # Sort by popularity in descending order
    response = sorted(response, key=lambda x: x['popularity'], reverse=True)

    # Return the top N words or all if less than N
    response = response[:limit]

    return jsonify(response)

@app.route('/substitute_words', methods=['POST'])
def substitute_words():
    request_data = request.get_json()
    word_to_replace = request_data.get('word')
    substitute_word = request_data.get('substitute')

    # Substitute words in the 'review' column
    affected_reviews = merged_df['review'].str.replace(word_to_replace, substitute_word, case=False).count()

    # Return the response
    response = {'affected_reviews': affected_reviews}
    return jsonify(response)

@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Implement logic to handle form submissions
        pass

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
