FROM phusion/baseimage:jammy-1.0.1

EXPOSE 80
EXPOSE 6080

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]


RUN echo 'APT::Get::Clean=always;' >> /etc/apt/apt.conf.d/99AutomaticClean

RUN apt-get update -qqy \
    && DEBIAN_FRONTEND=noninteractive apt-get -qyy install \
	--no-install-recommends \
	git \
	python3-venv \
	python3-dev \
	python3-lxml \
	libvirt-dev \
	zlib1g-dev \
	nginx \
	pkg-config \
	gcc \
	libldap2-dev \
	libssl-dev \
	libsasl2-dev \
	libsasl2-modules \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy only the requirements (speeds up subsequent builds)
COPY ./webvirtcloud/conf/requirements.txt /srv/webvirtcloud/conf/requirements.txt 

# Copy server specific config
COPY ./config/settings/settings.py /srv/webvirtcloud/webvirtcloud/settings.py

RUN chown -R www-data:www-data /srv/webvirtcloud

# Setup webvirtcloud
WORKDIR /srv/webvirtcloud
RUN python3 -m venv venv && \
	. venv/bin/activate && \
	pip3 install -U pip && \
	pip3 install wheel && \
	pip3 install -r conf/requirements.txt && \
	pip3 cache purge && \
	chown -R www-data:www-data /srv/webvirtcloud

# Copy common sources
COPY ./webvirtcloud /srv/webvirtcloud

RUN . venv/bin/activate && \
	python3 manage.py makemigrations && \
    python3 manage.py migrate && \
	python3 manage.py collectstatic --noinput && \
	chown -R www-data:www-data /srv/webvirtcloud

# Setup Nginx
RUN printf "\n%s" "daemon off;" >> /etc/nginx/nginx.conf && \
	rm /etc/nginx/sites-enabled/default && \
	chown -R www-data:www-data /var/lib/nginx

COPY ./webvirtcloud/conf/nginx/webvirtcloud.conf /etc/nginx/conf.d/

# Register services to runit
RUN	mkdir /etc/service/nginx && \
	mkdir /etc/service/nginx-log-forwarder && \
	mkdir /etc/service/webvirtcloud && \
	mkdir /etc/service/novnc
COPY ./webvirtcloud/conf/runit/nginx				/etc/service/nginx/run
COPY ./webvirtcloud/conf/runit/nginx-log-forwarder	/etc/service/nginx-log-forwarder/run
COPY ./webvirtcloud/conf/runit/novncd.sh			/etc/service/novnc/run
COPY ./webvirtcloud/conf/runit/webvirtcloud.sh		/etc/service/webvirtcloud/run

# Define mountable directories.
#VOLUME []

# Copy server specific configs:
COPY ./config/theme/flatly 				/srv/webvirtcloud/dev/scss/bootswatch/flatly
COPY ./config/wiki/README_USER_WIKI.md	/srv/webvirtcloud/wiki/content/README_USER_WIKI.md
RUN chown -R www-data:www-data 			/srv/webvirtcloud
RUN chmod -R 700 						/srv/webvirtcloud
COPY ./config/ssh 						/var/www/.ssh
RUN chown -R www-data 					/var/www/.ssh 
RUN chmod -R 700 						/var/www/.ssh
COPY ./config/nginx/nginx.conf 			/etc/nginx/nginx.conf
COPY ./config/nginx/webvirtcloud.conf	/etc/nginx/conf.d/webvirtcloud.conf

WORKDIR /srv/webvirtcloud
