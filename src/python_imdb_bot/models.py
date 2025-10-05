""" This module contains the data models for the IMDb bot. """
from typing import List, Optional, Literal
from pydantic import BaseModel, HttpUrl
import os
from dotenv import load_dotenv


class Rating(BaseModel):
    """
    Represents a rating for a movie or TV show.

    Attributes:
        Source (str): The source of the rating.
        Value (str): The value of the rating.
    """

    Source: str
    Value: str


class Media(BaseModel):
    """
    Represents a media item, such as a movie or a series.

    Attributes:
        Title (str): The title of the media.
        Year (str): The year of release.
        Rated (str): The rating of the media.
        Released (str): The release date of the media.
        Runtime (str): The duration of the media.
        Genre (str): The genre of the media.
        Director (str): The director of the media.
        Writer (str): The writer of the media.
        Actors (str): The actors in the media.
        Plot (str): The plot summary of the media.
        Language (str): The language of the media.
        Country (str): The country of origin of the media.
        Awards (str): The awards received by the media.
        Poster (HttpUrl): The URL of the poster image.
        Ratings (List[Rating]): The ratings given to the media.
        Metascore (Optional[str]): The Metascore rating of the media.
        imdbRating (str): The IMDb rating of the media.
        imdbVotes (str): The number of votes received on IMDb.
        imdbID (str): The IMDb ID of the media.
        Response (bool): The response status of the API request.
        Type (Literal["movie", "series"]): The type of the media (movie or series).
        DVD (Optional[str]): The DVD release date of the media.
        BoxOffice (Optional[str]): The box office earnings of the media.
        Production (Optional[str]): The production company of the media.
        Website (Optional[str]): The official website of the media.
        totalSeasons (Optional[str]): The total number of seasons for a series.
    """

    Title: str
    Year: str
    Rated: str
    Released: str
    Runtime: str
    Genre: str
    Director: str
    Writer: str
    Actors: str
    Plot: str
    Language: str
    Country: str
    Awards: str
    Poster: Optional[HttpUrl] = None
    Ratings: List[Rating]
    Metascore: Optional[str]
    imdbRating: str
    imdbVotes: str
    imdbID: str
    Response: bool
    Type: Literal["movie", "series"]
    DVD: Optional[str] = None
    BoxOffice: Optional[str] = None
    Production: Optional[str] = None
    Website: Optional[str] = None
    totalSeasons: Optional[str] = None


class Settings:
    """
    Represents the settings for the IMDb bot.

    Attributes:
        DISCORD_TOKEN (str): The Discord bot token.
        OMDB_API_KEY (str): The API key for the OMDB API.
        SUPABASE_KEY (str): The API key for the Supabase database.
        SUPABASE_URL (str): The URL of the Supabase database.
        CHANNEL_ID (int): The ID of the Discord channel where the bot will operate.
        LOG_LEVEL (str, optional): The log level for the bot. Defaults to "INFO".
        LOG_FILE (str, optional): The file path for the log file. Defaults to "imdb_bot.log".
        LOG_FORMAT (str, optional): The log format for the log messages.
          Defaults to "%(asctime)s - %(name)s - %(levelname)s - %(message)s".

    """

    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
        self.OMDB_API_KEY = os.getenv('OMDB_API_KEY', '')
        self.SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
        self.SUPABASE_URL = os.getenv('SUPABASE_URL', '')
        self.TMDB_API_KEY = os.getenv('TMDB_API_KEY', '')
        self.CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', '/app/logs/bot.log')
        self.LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class URLInfo(BaseModel):
    IMDB_URI: str
    IMDB_ID: str
    USER_RATING: Optional[str] = None
